"""成员 C：分段退款及取消状态持久化；提前时间由调用方注入。"""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from . import config
from .errors import DomainError
from .models import Booking
from .pricing import round_money
from .repositories import Repository
from .validation import validate_cancel_hours


def refund_ratio(hours_before_start: object) -> Decimal:
    """提前 >=24 小时全退，>=2 小时半退，否则不退。"""
    hours = validate_cancel_hours(hours_before_start)
    if hours >= config.FULL_REFUND_HOURS:
        return Decimal("1.00")
    elif hours >= config.HALF_REFUND_HOURS:
        return Decimal("0.50")
    else:
        return Decimal("0.00")


def calculate_refund(fee: object, hours_before_start: object) -> float:
    """按原费用乘退款比例，使用十进制并四舍五入到分。"""
    ratio = refund_ratio(hours_before_start)
    if isinstance(fee, bool) or not isinstance(fee, (int, float, Decimal)):
        raise DomainError("E_FEE_RANGE")
    amount = Decimal(str(fee))
    if not amount.is_finite() or amount < 0:
        raise DomainError("E_FEE_RANGE")
    refund = amount * ratio
    return round_money(refund)


def hours_before_booking(booking: Booking, now: datetime) -> float:
    """用调用方提供的当地时间计算提前小时数；范围交由退款函数校验。"""
    start = datetime.fromisoformat(booking.date).replace(hour=booking.start_hour,
                                                       tzinfo=now.tzinfo)
    return (start - now).total_seconds() / 3600


class CancellationService:
    """仅允许 confirmed 预约取消，更新时保持原始费用。"""

    def __init__(self, bookings: Repository[Booking]) -> None:
        """注入与预约模块共享的仓库。"""
        self.bookings = bookings

    def cancel_booking(self, booking_id: str, hours_before_start: object) -> Booking:
        """以显式提前小时数取消；重复取消和其他状态不允许。"""
        validate_cancel_hours(hours_before_start)
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise DomainError("E_BOOKING_NOT_FOUND")
        if booking.status != "confirmed":
            raise DomainError("E_BOOKING_NOT_CANCELLABLE")
        refund = calculate_refund(booking.fee, hours_before_start)
        cancelled = replace(booking, status="cancelled", refund=refund)
        self.bookings.update(cancelled)
        return cancelled

    def preview_cancel(self, booking_id: str, hours_before_start: object) -> dict[str, object]:
        """只读退款预览，复用同一资格、比例和金额函数；不改变预约。"""
        hours = validate_cancel_hours(hours_before_start)
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise DomainError("E_BOOKING_NOT_FOUND")
        if booking.status != "confirmed":
            raise DomainError("E_BOOKING_NOT_CANCELLABLE")
        return {"booking_id": booking.booking_id, "hours_before_start": float(hours),
                "refund_ratio": float(refund_ratio(hours)),
                "refund": calculate_refund(booking.fee, hours), "fee": booking.fee}
