"""数据结构；不包含交互或业务判断。"""

from dataclasses import dataclass
from typing import Literal

from .config import OPEN_HOUR, CLOSE_HOUR

Role = Literal["student", "teacher"]
UserStatus = Literal["active", "suspended"]
VenueType = Literal["badminton", "table_tennis", "basketball"]
BookingStatus = Literal["confirmed", "cancelled", "completed", "no_show"]


@dataclass(frozen=True)
class User:
    """校园用户；冻结实例使仓库更新必须显式进行。"""

    user_id: str
    name: str
    role: Role
    status: UserStatus
    violation_count: int


@dataclass(frozen=True)
class Venue:
    """统一 08:00～22:00 营业的运动场馆。"""

    venue_id: str
    name: str
    venue_type: VenueType
    capacity: int
    base_rate: float
    open_hour: int = OPEN_HOUR
    close_hour: int = CLOSE_HOUR


@dataclass(frozen=True)
class Booking:
    """预约记录；date 使用严格 ISO 日期字符串，金额精确到分。"""

    booking_id: str
    user_id: str
    venue_id: str
    date: str
    start_hour: int
    duration: int
    participants: int
    status: BookingStatus = "confirmed"
    fee: float = 0.0
    refund: float = 0.0
