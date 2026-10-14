"""JSON API Controller；只调用共享服务并返回统一响应。"""

from dataclasses import asdict
from typing import Any

from flask import Blueprint, jsonify, request, session

from ..errors import DomainError
from . import get_services, today
from .adapters import booking_arguments, statistics_arguments

api = Blueprint("api",__name__,url_prefix="/api")


def _payload() -> dict[str, Any]:
    if not request.is_json:
        raise DomainError("E_REQUEST_FORMAT")
    result = request.get_json(silent=True)
    if not isinstance(result,dict):
        raise DomainError("E_REQUEST_FORMAT")
    return result


@api.get("/venues")
def venues() -> Any:
    """返回固定排序的全部场馆。"""
    return jsonify(success=True,data=[asdict(item) for item in get_services()[0].list_venues()])


@api.post("/bookings")
def create_booking() -> Any:
    """创建预约；用户属性取自仓库，JSON 数字不隐式转换。"""
    values = _payload()
    booking = get_services()[0].create_booking(**booking_arguments(values,values.get("user_id")))
    return jsonify(success=True,data=asdict(booking)),201


@api.get("/users/<user_id>/bookings")
def user_bookings(user_id: str) -> Any:
    """查询指定用户的全部预约。"""
    return jsonify(success=True,data=[asdict(item) for item in get_services()[0].list_user_bookings(user_id)])


@api.get("/bookings/<booking_id>")
def booking_detail(booking_id: str) -> Any:
    """返回完整预约详情和后端原始费用。"""
    return jsonify(success=True,data=get_services()[0].booking_details(booking_id))


@api.post("/bookings/<booking_id>/cancel-preview")
def cancel_preview(booking_id: str) -> Any:
    """只读退款预览，不更新状态。"""
    result = get_services()[1].preview_cancel(booking_id,_payload().get("hours_before_start"))
    return jsonify(success=True,data=result)


@api.post("/bookings/<booking_id>/cancel")
def cancel_booking(booking_id: str) -> Any:
    """复用 Service 执行取消，并返回后端计算的比例和金额。"""
    hours = _payload().get("hours_before_start")
    cancellation = get_services()[1]
    preview = cancellation.preview_cancel(booking_id,hours)
    booking = cancellation.cancel_booking(booking_id,hours)
    return jsonify(success=True,data={**asdict(booking),"refund_ratio":preview["refund_ratio"]})


@api.get("/statistics")
def statistics() -> Any:
    """返回 Service 报表，total_hours 为契约中的时长字段。"""
    report = get_services()[2].build_report(**statistics_arguments(request.args,today()))
    return jsonify(success=True,data={**asdict(report),"total_hours":report.total_booked_hours})


@api.post("/current-user")
def switch_user() -> Any:
    """从固定仓库选择当前测试用户，不接受 role/status 等覆盖。"""
    user = get_services()[0].get_user(_payload().get("user_id"))
    session["user_id"] = user.user_id
    return jsonify(success=True,data=asdict(user))
