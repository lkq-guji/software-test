"""装配可替换仓库和业务服务，CLI 只调用这里及服务方法。"""

from pathlib import Path

from .booking_service import BookingService
from .cancellation import CancellationService
from .repositories import MemoryRepository, json_repositories
from .seed_data import sample_users, sample_venues
from .statistics import StatisticsService

Services = tuple[BookingService, CancellationService, StatisticsService]


def create_services(data_dir: str | Path) -> Services:
    """初始化缺失数据文件，保留已有内容，装配共享 JSON 仓库。"""
    users, venues, bookings = json_repositories(data_dir)
    users.initialize(sample_users())
    venues.initialize(sample_venues())
    bookings.initialize()
    return BookingService(users, venues, bookings), CancellationService(bookings), StatisticsService(venues, bookings)


def create_memory_services() -> Services:
    """用固定数据装配完全隔离的内存服务，供演示与测试使用。"""
    users = MemoryRepository("user_id", sample_users())
    venues = MemoryRepository("venue_id", sample_venues())
    bookings = MemoryRepository("booking_id")
    return BookingService(users, venues, bookings), CancellationService(bookings), StatisticsService(venues, bookings)
