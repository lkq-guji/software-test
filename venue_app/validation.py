"""成员 A：格式和取值范围校验，所有范围来自 config。"""

from datetime import date as calendar_date
from decimal import Decimal, InvalidOperation

from . import config
from .errors import DomainError
from .models import User, Venue


def validate_integer(value: object, bounds: tuple[int, int], code: str) -> int:
    """校验闭区间内的整数；拒绝 bool、浮点数和字符串。"""
    if type(value) is not int or not bounds[0] <= value <= bounds[1]:
        raise DomainError(code)
    return value


def validate_number(value: object, bounds: tuple[int, int], code: str) -> Decimal:
    """校验有限 int/float/Decimal 数值，并以十进制返回。"""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise DomainError(code)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DomainError(code) from None
    if not number.is_finite() or not bounds[0] <= number <= bounds[1]:
        raise DomainError(code)
    return number


def validate_user_id(user_id: object) -> str:
    """校验非空、全部为数字且长度为 8～12 的用户编号。"""
    if user_id is None or user_id == "":
        raise DomainError("E_USER_ID_EMPTY")
    if not isinstance(user_id, str) or not user_id.isdigit():
        raise DomainError("E_USER_ID_NON_DIGIT")
    if not config.USER_ID_LENGTH[0] <= len(user_id) <= config.USER_ID_LENGTH[1]:
        raise DomainError("E_USER_ID_LENGTH")
    return user_id


def validate_duration(duration: object) -> int:
    """校验 1～4 小时的整数时长。"""
    return validate_integer(duration, config.DURATION_RANGE, "E_DURATION_RANGE")


def validate_participants(participants: object) -> int:
    """校验 1～30 人的整数人数。"""
    return validate_integer(participants, config.PARTICIPANTS_RANGE, "E_PARTICIPANTS_RANGE")


def validate_capacity(capacity: object) -> int:
    """校验场馆容量 1～30 人。"""
    return validate_integer(capacity, config.CAPACITY_RANGE, "E_CAPACITY_RANGE")


def validate_base_rate(base_rate: object) -> Decimal:
    """校验基础费率 10～200 元/小时。"""
    return validate_number(base_rate, config.BASE_RATE_RANGE, "E_BASE_RATE_RANGE")


def validate_start_hour(start_hour: object) -> int:
    """校验 8～21 的整数开始小时；结束时间关系在业务层判断。"""
    return validate_integer(start_hour, config.START_HOUR_RANGE, "E_OUTSIDE_OPEN_HOURS")


def validate_date(value: object) -> str:
    """校验真实 YYYY-MM-DD 日期，不额外限制过去/未来日期。"""
    if not isinstance(value, str):
        raise DomainError("E_DATE_FORMAT")
    try:
        parsed = calendar_date.fromisoformat(value)
    except ValueError:
        raise DomainError("E_DATE_FORMAT") from None
    if parsed.isoformat() != value:
        raise DomainError("E_DATE_FORMAT")
    return value


def validate_violation_count(value: object) -> int:
    """校验违规次数输入域 0～5；是否允许预约由模块 B 判断。"""
    return validate_integer(value, config.VIOLATION_COUNT_RANGE, "E_VIOLATION_COUNT_RANGE")


def validate_daily_booking_count(value: object) -> int:
    """校验资格函数的已有预约数输入域 0～2。"""
    return validate_integer(value, config.DAILY_BOOKING_COUNT_RANGE, "E_DAILY_BOOKING_COUNT_RANGE")


def validate_role(role: object) -> str:
    """校验 student/teacher 身份。"""
    if not isinstance(role, str) or role not in config.VALID_ROLES:
        raise DomainError("E_ROLE_INVALID")
    return role


def validate_user(user: User) -> None:
    """校验用户模型的编号、身份、状态枚举和违规次数。"""
    validate_user_id(user.user_id)
    validate_role(user.role)
    if not isinstance(user.status, str) or user.status not in config.VALID_USER_STATUSES:
        raise DomainError("E_STATUS_INVALID")
    validate_violation_count(user.violation_count)


def validate_venue(venue: Venue) -> None:
    """校验容量、费率、类型和统一营业时间。"""
    validate_capacity(venue.capacity)
    validate_base_rate(venue.base_rate)
    if not isinstance(venue.venue_type, str) or venue.venue_type not in config.VALID_VENUE_TYPES:
        raise DomainError("E_VENUE_TYPE_INVALID")
    if type(venue.open_hour) is not int or type(venue.close_hour) is not int:
        raise DomainError("E_OUTSIDE_OPEN_HOURS")
    if venue.open_hour != config.OPEN_HOUR or venue.close_hour != config.CLOSE_HOUR:
        raise DomainError("E_OUTSIDE_OPEN_HOURS")


def validate_booking_input(
    user_id: object, booking_date: object, start_hour: object,
    duration: object, participants: object,
) -> None:
    """校验预约所有输入域；资格、容量和时段关系由模块 B 判断。"""
    validate_user_id(user_id)
    validate_date(booking_date)
    validate_duration(duration)
    validate_participants(participants)
    validate_start_hour(start_hour)


def validate_cancel_hours(hours_before_start: object) -> Decimal:
    """校验提前取消时间 0～168 小时；允许小数小时。"""
    return validate_number(hours_before_start, config.CANCEL_HOURS_RANGE, "E_CANCEL_HOURS_RANGE")


def validate_statistics_input(days: object, top_n: object, threshold: object) -> None:
    """校验统计天数、Top-N 和整数使用率阈值。"""
    validate_integer(days, config.STAT_DAYS_RANGE, "E_STAT_DAYS_RANGE")
    validate_integer(top_n, config.TOP_N_RANGE, "E_TOP_N_RANGE")
    validate_integer(threshold, config.UTILIZATION_THRESHOLD_RANGE, "E_UTILIZATION_THRESHOLD_RANGE")
