"""请求类型转换：不修正非法值，不替代业务校验。"""

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ..errors import DomainError


def form_integer(value: object, code: str) -> int:
    """HTML/query 字符串转整数；JSON API 不使用此转换，保留原类型。"""
    if not isinstance(value,str):
        raise DomainError(code)
    try:
        return int(value)
    except ValueError:
        raise DomainError(code) from None


def form_hours(value: object) -> Decimal:
    """把表单小时数转换为 Decimal，范围由 CancellationService 判断。"""
    if not isinstance(value,str):
        raise DomainError("E_CANCEL_HOURS_RANGE")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise DomainError("E_CANCEL_HOURS_RANGE") from None


def booking_arguments(values: Mapping[str, Any], user_id: str, *, html: bool = False) -> dict[str, Any]:
    """映射请求字段到现有 Service 参数，仅 HTML 字符串做类型转换。"""
    if not isinstance(values.get("venue_id"),str):
        raise DomainError("E_REQUEST_FORMAT")
    integer_fields = {"start_hour":"E_OUTSIDE_OPEN_HOURS", "duration":"E_DURATION_RANGE",
                      "participants":"E_PARTICIPANTS_RANGE"}
    converted = {field: form_integer(values.get(field),code) if html else values.get(field)
                 for field,code in integer_fields.items()}
    return dict(user_id=user_id,venue_id=values.get("venue_id"),booking_date=values.get("date"),**converted)


def statistics_arguments(values: Mapping[str, Any], default_date: str) -> dict[str, Any]:
    """转换统计 query/form 字段，所有域检查留在 StatisticsService。"""
    return dict(start_date=values.get("start_date",default_date),
                days=form_integer(values.get("days","7"),"E_STAT_DAYS_RANGE"),
                top_n=form_integer(values.get("top_n","5"),"E_TOP_N_RANGE"),
                min_utilization_percent=form_integer(values.get("min_utilization_percent","50"),
                                                     "E_UTILIZATION_THRESHOLD_RANGE"))
