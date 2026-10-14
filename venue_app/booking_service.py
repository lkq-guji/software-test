"""成员 B：资格、营业关系、容量、半开区间冲突和预约创建。"""

from . import config
from .errors import DomainError
from .models import Booking, User, Venue
from .pricing import calculate_fee, calculate_raw_fee, round_money
from .repositories import Repository
from .validation import (
    validate_booking_input, validate_daily_booking_count, validate_date,
    validate_duration, validate_participants, validate_start_hour,
    validate_user, validate_user_id, validate_venue,
)


def check_user_eligibility(user: User, daily_booking_count: object) -> bool:
    """输入域校验后按状态、违规、每日限额顺序判断；失败抛明确错误码。"""
    validate_user(user)
    count = validate_daily_booking_count(daily_booking_count)
    if user.status != "active":
        raise DomainError("E_USER_SUSPENDED")
    if user.violation_count >= config.VIOLATION_LIMIT:
        raise DomainError("E_TOO_MANY_VIOLATIONS")
    if count >= config.DAILY_BOOKING_LIMIT:
        raise DomainError("E_DAILY_BOOKING_LIMIT")
    return True


def check_open_hours(start_hour: object, duration: object) -> bool:
    """检查开始、时长的输入域及结束时间不超过 22 点。"""
    start = validate_start_hour(start_hour)
    hours = validate_duration(duration)
    if start + hours > config.CLOSE_HOUR:
        raise DomainError("E_OUTSIDE_OPEN_HOURS")
    return True


def check_capacity(participants: object, venue: Venue) -> bool:
    """人数须在 1～30 输入域内，且不得超过场馆容量。"""
    people = validate_participants(participants)
    validate_venue(venue)
    if people > venue.capacity:
        raise DomainError("E_CAPACITY_EXCEEDED")
    return True


def is_time_conflict(start1: int, end1: int, start2: int, end2: int) -> bool:
    """严格实现半开区间 [start,end) 重叠公式，相邻端点不冲突。"""
    return max(start1, start2) < min(end1, end2)


def can_create_booking(
    user: User, venue: Venue, booking_date: str, start_hour: int,
    duration: int, participants: int, existing_bookings: list[Booking],
) -> bool:
    """纯预约判定；输入域优先，再按资格→营业→容量→冲突返回首错。"""
    validate_booking_input(user.user_id, booking_date, start_hour, duration, participants)
    validate_user(user)
    validate_venue(venue)
    effective = [booking for booking in existing_bookings
                 if booking.status in config.EFFECTIVE_BOOKING_STATUSES]
    daily_count = sum(booking.user_id == user.user_id and booking.date == booking_date
                      for booking in effective)
    check_user_eligibility(user, daily_count)
    check_open_hours(start_hour, duration)
    check_capacity(participants, venue)
    for booking in effective:
        if booking.venue_id == venue.venue_id and booking.date == booking_date:
            if is_time_conflict(start_hour, start_hour + duration,
                                booking.start_hour, booking.start_hour + booking.duration):
                raise DomainError("E_TIME_CONFLICT")
    return True


class BookingService:
    """编排仓库交互与纯业务函数；不使用随机数或系统当前时间。"""

    def __init__(self, users: Repository[User], venues: Repository[Venue],
                 bookings: Repository[Booking]) -> None:
        """注入可替换的用户、场馆和预约仓库。"""
        self.users = users
        self.venues = venues
        self.bookings = bookings

    def list_venues(self) -> list[Venue]:
        """返回按 venue_id 升序排列的合法场馆。"""
        venues = self.venues.list_all()
        for venue in venues:
            validate_venue(venue)
        return sorted(venues, key=lambda venue: venue.venue_id)

    def list_users(self) -> list[User]:
        """返回经校验、按编号排序的测试用户，供 Web 切换使用。"""
        users = self.users.list_all()
        for user in users:
            validate_user(user)
        return sorted(users, key=lambda user: user.user_id)

    def get_user(self, user_id: str) -> User:
        """从仓库获取真实身份和状态，不接受前端伪造用户属性。"""
        validate_user_id(user_id)
        user = self.users.get(user_id)
        if user is None:
            raise DomainError("E_USER_NOT_FOUND")
        validate_user(user)
        return user

    def get_venue(self, venue_id: str) -> Venue:
        """查询并校验场馆，缺失时返回统一错误码。"""
        venue = self.venues.get(venue_id)
        if venue is None:
            raise DomainError("E_VENUE_NOT_FOUND")
        validate_venue(venue)
        return venue

    def booking_details(self, booking_id: str) -> dict[str, object]:
        """组装完整预约详情，原始费用由 pricing 模块计算。"""
        from dataclasses import asdict
        booking = self.get_booking(booking_id)
        venue = self.get_venue(booking.venue_id)
        user = self.get_user(booking.user_id)
        return {**asdict(booking), "venue": asdict(venue), "user": asdict(user),
                "end_hour": booking.start_hour + booking.duration,
                "raw_fee": round_money(calculate_raw_fee(venue.base_rate, booking.duration))}

    def overview(self, user_id: str, today: str) -> dict[str, int]:
        """按注入日期返回首页真实概览，统计口径复用统计模块。"""
        from .statistics import build_venue_statistics
        mine = self.list_user_bookings(user_id)
        venues = self.list_venues()
        report = build_venue_statistics(venues, self.bookings.list_all(), today, 1, 3, 0)
        return {"venue_count": len(venues),
                "my_effective_bookings": sum(item.status in config.EFFECTIVE_BOOKING_STATUSES for item in mine),
                "today_bookings": report.total_bookings,
                "today_hours": report.total_booked_hours}

    def list_user_bookings(self, user_id: str) -> list[Booking]:
        """查询指定用户全部状态的预约；用户必须存在。"""
        validate_user_id(user_id)
        if self.users.get(user_id) is None:
            raise DomainError("E_USER_NOT_FOUND")
        return sorted((booking for booking in self.bookings.list_all()
                       if booking.user_id == user_id),
                      key=lambda booking: (booking.date, booking.start_hour, booking.booking_id))

    def available_venues(self, booking_date: str, start_hour: int,
                         duration: int, participants: int = 1) -> list[Venue]:
        """按日期、时段和人数查询空闲且容量足够的场馆。"""
        validate_date(booking_date)
        check_open_hours(start_hour, duration)
        validate_participants(participants)
        existing = self.bookings.list_all()
        return [venue for venue in self.list_venues()
                if participants <= venue.capacity
                and not any(booking.venue_id == venue.venue_id
                            and booking.date == booking_date
                            and booking.status in config.EFFECTIVE_BOOKING_STATUSES
                            and is_time_conflict(start_hour, start_hour + duration,
                                                 booking.start_hour,
                                                 booking.start_hour + booking.duration)
                            for booking in existing)]

    def get_booking(self, booking_id: str) -> Booking:
        """按预约编号查询；不存在时抛 E_BOOKING_NOT_FOUND。"""
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise DomainError("E_BOOKING_NOT_FOUND")
        return booking

    def create_booking(self, user_id: str, venue_id: str, booking_date: str,
                       start_hour: int, duration: int, participants: int) -> Booking:
        """通过全部规则后计费并持久化 confirmed 预约；失败不写仓库。"""
        validate_booking_input(user_id, booking_date, start_hour, duration, participants)
        user = self.users.get(user_id)
        if user is None:
            raise DomainError("E_USER_NOT_FOUND")
        venue = self.venues.get(venue_id)
        if venue is None:
            raise DomainError("E_VENUE_NOT_FOUND")
        existing = self.bookings.list_all()
        can_create_booking(user, venue, booking_date, start_hour, duration, participants, existing)
        fee = calculate_fee(venue.base_rate, duration, start_hour, user.role)
        booking = Booking(self._next_id(existing), user_id, venue_id, booking_date,
                          start_hour, duration, participants, fee=fee)
        self.bookings.add(booking)
        return booking

    @staticmethod
    def _next_id(existing: list[Booking]) -> str:
        numbers = [int(booking.booking_id[1:]) for booking in existing
                   if booking.booking_id.startswith("B")
                   and booking.booking_id[1:].isascii()
                   and booking.booking_id[1:].isdigit()]
        return f"B{max(numbers, default=0) + 1:06d}"
