"""成员 D：循环聚合、稳定 Top-N 和使用率阈值过滤。"""

from dataclasses import dataclass
from datetime import date as calendar_date
from decimal import Decimal

from . import config
from .models import Booking, Venue
from .pricing import round_money
from .repositories import Repository
from .validation import validate_date, validate_statistics_input, validate_venue


@dataclass(frozen=True)
class VenueStatistics:
    """单场馆有效预约、占用时长、净收入和使用率。"""

    venue_id: str
    name: str
    booking_count: int
    booked_hours: int
    available_hours: int
    revenue: float
    utilization_percent: float


@dataclass(frozen=True)
class StatisticsReport:
    """全场馆统计；Top-N 与阈值过滤为两个独立结果。"""

    start_date: str
    days: int
    total_bookings: int
    total_booked_hours: int
    total_revenue: float
    utilization_percent: float
    venues: list[VenueStatistics]
    top_venues: list[VenueStatistics]
    filtered_venues: list[VenueStatistics]


def build_venue_statistics(
    venues: list[Venue], bookings: list[Booking], start_date: str,
    days: int, top_n: int, min_utilization_percent: int,
) -> StatisticsReport:
    """统计从 start_date 起连续 days 天，只纳入 confirmed/completed。

    日期范围为 [start_date, start_date + days)。收入扣除有效记录的 refund；
    cancelled/no_show 全记录排除。Top-N 只返回有有效预约的场馆。
    使用率阈值按未舍入值比较，显示值保留两位小数。
    """
    validate_date(start_date)
    validate_statistics_input(days, top_n, min_utilization_percent)
    start_ordinal = calendar_date.fromisoformat(start_date).toordinal()
    end_ordinal = start_ordinal + days
    available_hours = days * config.HOURS_PER_DAY
    counters: dict[str, list[int | Decimal]] = {}
    for venue in venues:
        validate_venue(venue)
        counters[venue.venue_id] = [0, 0, Decimal("0")]
    for booking in bookings:
        if booking.status not in config.EFFECTIVE_BOOKING_STATUSES:
            continue
        if booking.venue_id not in counters:
            continue
        validate_date(booking.date)
        booking_ordinal = calendar_date.fromisoformat(booking.date).toordinal()
        if not start_ordinal <= booking_ordinal < end_ordinal:
            continue
        aggregate = counters[booking.venue_id]
        aggregate[0] += 1
        aggregate[1] += booking.duration
        aggregate[2] += Decimal(str(booking.fee)) - Decimal(str(booking.refund))
    rows: list[VenueStatistics] = []
    filtered: list[VenueStatistics] = []
    total_bookings = 0
    total_booked_hours = 0
    total_revenue = Decimal("0")
    for venue in sorted(venues, key=lambda item: item.venue_id):
        booking_count, booked_hours, revenue = counters[venue.venue_id]
        utilization = booked_hours / available_hours * 100
        row = VenueStatistics(venue.venue_id, venue.name, int(booking_count),
                              int(booked_hours), available_hours,
                              round_money(revenue), round(utilization, 2))
        rows.append(row)
        if booked_hours * 100 >= min_utilization_percent * available_hours:
            filtered.append(row)
        total_bookings += int(booking_count)
        total_booked_hours += int(booked_hours)
        total_revenue += revenue
    ranking = sorted((row for row in rows if row.booking_count > 0),
                     key=lambda row: (-row.booking_count, row.venue_id))
    total_available = available_hours * len(venues)
    total_utilization = total_booked_hours / total_available * 100 if total_available else 0.0
    return StatisticsReport(start_date, days, total_bookings, total_booked_hours,
                            round_money(total_revenue), round(total_utilization, 2),
                            rows, ranking[:top_n], filtered)


class StatisticsService:
    """将仓库快照传给纯统计函数。"""

    def __init__(self, venues: Repository[Venue], bookings: Repository[Booking]) -> None:
        """注入场馆与预约仓库。"""
        self.venues = venues
        self.bookings = bookings

    def build_report(self, start_date: str, days: int = 7, top_n: int = 5,
                     min_utilization_percent: int = 50) -> StatisticsReport:
        """按明确起始日期生成可重复的统计报表。"""
        return build_venue_statistics(self.venues.list_all(), self.bookings.list_all(),
                                      start_date, days, top_n, min_utilization_percent)
