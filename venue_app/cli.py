"""中文命令行交互；输入转换、显示与服务调用，不复制业务规则。"""

import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .application import Services, create_memory_services, create_services
from .errors import DomainError
from .models import Booking, Venue
from .statistics import StatisticsReport

Input = Callable[[str], str]
Output = Callable[[str], None]
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read_integer(input_fn: Input, prompt: str, code: str) -> int:
    try:
        return int(input_fn(prompt))
    except ValueError:
        raise DomainError(code) from None


def _read_hours(input_fn: Input) -> Decimal:
    try:
        return Decimal(input_fn("提前取消小时数（0～168，可含小数）："))
    except InvalidOperation:
        raise DomainError("E_CANCEL_HOURS_RANGE") from None


def display_venues(venues: list[Venue], output: Output = print) -> None:
    """显示场馆编号、容量、费率和营业时间。"""
    for venue in venues:
        output(f"{venue.venue_id} | {venue.name} | 容量 {venue.capacity} 人 | "
               f"{venue.base_rate:.2f} 元/小时 | {venue.open_hour:02d}:00～{venue.close_hour:02d}:00")
    if not venues:
        output("没有符合条件的场馆。")


def display_booking(booking: Booking, output: Output = print) -> None:
    """显示预约记录和两位小数金额。"""
    output(f"{booking.booking_id} | {booking.user_id} | {booking.venue_id} | {booking.date} "
           f"{booking.start_hour:02d}:00～{booking.start_hour + booking.duration:02d}:00 | "
           f"{booking.participants} 人 | {booking.status} | "
           f"费用 {booking.fee:.2f} 元 | 退款 {booking.refund:.2f} 元")


def display_report(report: StatisticsReport, output: Output = print) -> None:
    """显示统计总览、各场馆、Top-N 和阈值过滤结果。"""
    output(f"从 {report.start_date} 起 {report.days} 天：有效预约 {report.total_bookings} 次，"
           f"累计 {report.total_booked_hours} 小时，收入 {report.total_revenue:.2f} 元，"
           f"总使用率 {report.utilization_percent:.2f}%")
    for row in report.venues:
        output(f"{row.venue_id} {row.name} | {row.booking_count} 次 | {row.booked_hours} 小时 | "
               f"收入 {row.revenue:.2f} 元 | 使用率 {row.utilization_percent:.2f}%")
    output("Top-N：" + (", ".join(row.venue_id for row in report.top_venues) or "空列表"))
    output("达到使用率阈值的场馆：" + (", ".join(row.venue_id for row in report.filtered_venues) or "空列表"))


def run_cli(services: Services, input_fn: Input = input, output: Output = print) -> None:
    """运行六项菜单；DomainError 友好显示，EOF/Ctrl+C 正常退出。"""
    booking_service, cancellation_service, statistics_service = services
    output("校园运动场馆预约与计费系统")
    while True:
        output("\n1. 查看场馆\n2. 创建预约\n3. 查看我的预约\n4. 取消预约\n5. 场馆统计\n6. 退出")
        try:
            choice = input_fn("请选择：").strip()
            if choice == "1":
                display_venues(booking_service.list_venues(), output)
                if input_fn("查询指定时段空闲场馆？（y/N）：").strip().lower() == "y":
                    day = input_fn("日期（YYYY-MM-DD）：")
                    start = _read_integer(input_fn, "开始小时（8～21）：", "E_OUTSIDE_OPEN_HOURS")
                    duration = _read_integer(input_fn, "时长（1～4）：", "E_DURATION_RANGE")
                    people = _read_integer(input_fn, "参与人数（1～30）：", "E_PARTICIPANTS_RANGE")
                    display_venues(booking_service.available_venues(day, start, duration, people), output)
            elif choice == "2":
                user_id = input_fn("用户编号：")
                venue_id = input_fn("场馆编号：")
                day = input_fn("预约日期（YYYY-MM-DD）：")
                start = _read_integer(input_fn, "开始小时（8～21）：", "E_OUTSIDE_OPEN_HOURS")
                duration = _read_integer(input_fn, "时长（1～4）：", "E_DURATION_RANGE")
                people = _read_integer(input_fn, "参与人数（1～30）：", "E_PARTICIPANTS_RANGE")
                booking = booking_service.create_booking(user_id, venue_id, day, start, duration, people)
                output("预约成功。")
                display_booking(booking, output)
            elif choice == "3":
                bookings = booking_service.list_user_bookings(input_fn("用户编号："))
                for booking in bookings:
                    display_booking(booking, output)
                if not bookings:
                    output("该用户暂无预约。")
            elif choice == "4":
                booking_id = input_fn("预约编号：")
                cancelled = cancellation_service.cancel_booking(booking_id, _read_hours(input_fn))
                output("取消成功。")
                display_booking(cancelled, output)
            elif choice == "5":
                day = input_fn("统计起始日期（YYYY-MM-DD）：")
                days = _read_integer(input_fn, "统计天数（1～31）：", "E_STAT_DAYS_RANGE")
                top_n = _read_integer(input_fn, "Top-N（1～10）：", "E_TOP_N_RANGE")
                threshold = _read_integer(input_fn, "使用率阈值（0～100）：", "E_UTILIZATION_THRESHOLD_RANGE")
                display_report(statistics_service.build_report(day, days, top_n, threshold), output)
            elif choice == "6":
                output("已退出。")
                return
            else:
                raise DomainError("E_MENU_CHOICE")
        except DomainError as error:
            output(f"{error.code}：{error.message}")
        except (EOFError, KeyboardInterrupt):
            output("\n已退出。")
            return


def run_demo(output: Output = print) -> None:
    """在固定日期执行查询→预约→冲突拒绝→取消→再预约→统计。"""
    booking, cancellation, statistics = create_memory_services()
    output("固定演示日期：2026-10-20；数据保存在本次演示的内存仓库。")
    display_venues(booking.list_venues(), output)
    first = booking.create_booking("20260001", "V001", "2026-10-20", 18, 2, 4)
    display_booking(first, output)
    try:
        booking.create_booking("20260003", "V001", "2026-10-20", 19, 1, 2)
    except DomainError as error:
        output(f"冲突测试：{error.code}：{error.message}")
    display_report(statistics.build_report("2026-10-20", 1, 3, 0), output)
    display_booking(cancellation.cancel_booking(first.booking_id, 2), output)
    second = booking.create_booking("20260003", "V001", "2026-10-20", 18, 2, 2)
    display_booking(second, output)
    display_report(statistics.build_report("2026-10-20", 1, 3, 0), output)


def main(argv: list[str] | None = None) -> int:
    """解析命令行并启动交互/固定演示；初始化错误返回退出码 1。"""
    parser = argparse.ArgumentParser(description="校园运动场馆预约与计费系统")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="JSON 数据目录")
    parser.add_argument("--demo", action="store_true", help="运行固定、隔离的完整演示")
    args = parser.parse_args(argv)
    try:
        if args.demo:
            run_demo()
        else:
            run_cli(create_services(args.data_dir))
    except DomainError as error:
        print(f"{error.code}：{error.message}")
        return 1
    return 0
