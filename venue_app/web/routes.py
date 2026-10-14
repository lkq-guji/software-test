"""Jinja 页面 Controller；业务判定全部来自 Service。"""

from typing import Any

from flask import Blueprint, redirect, render_template, request, session, url_for

from ..errors import DomainError
from . import current_user_id, get_services, today
from .adapters import booking_arguments, form_hours, statistics_arguments
from .presenters import error_status, safe_error

pages = Blueprint("pages",__name__)


@pages.get("/")
def index() -> str:
    """显示真实首页概览和前三个场馆。"""
    service = get_services()[0]
    return render_template("index.html",overview=service.overview(current_user_id(),today()),
                           venues=service.list_venues()[:3],today=today())


@pages.get("/venues")
def venues() -> str:
    """场馆列表支持类型展示筛选，不改变业务数据。"""
    category = request.args.get("venue_type","")
    items = get_services()[0].list_venues()
    return render_template("venues.html",venues=[v for v in items if not category or v.venue_type == category],
                           category=category)


@pages.route("/bookings/new",methods=["GET","POST"])
def create_booking() -> Any:
    """提交使用 Session 用户；失败保留表单原值及字段错误。"""
    service = get_services()[0]
    values = dict(request.form) if request.method == "POST" else {
        "venue_id":request.args.get("venue_id","V001"),"date":today(),
        "start_hour":"14","duration":"2","participants":"2"}
    error,status = None,200
    if request.method == "POST":
        try:
            booking = service.create_booking(**booking_arguments(values,current_user_id(),html=True))
            session["created_booking"] = booking.booking_id
            return redirect(url_for("pages.booking_detail",booking_id=booking.booking_id),303)
        except DomainError as failure:
            error,status = safe_error(failure),error_status(failure.code)
    return render_template("booking_create.html",venues=service.list_venues(),values=values,error=error),status


@pages.get("/venues/<venue_id>")
def venue_detail(venue_id: str) -> str:
    """展示 Service 返回的完整场馆基础信息。"""
    return render_template("venue_detail.html",venue=get_services()[0].get_venue(venue_id))


@pages.get("/bookings")
def my_bookings() -> str:
    """当前用户预约按原 Service 固定顺序展示。"""
    service = get_services()[0]
    names = {venue.venue_id:venue.name for venue in service.list_venues()}
    return render_template("my_bookings.html",bookings=service.list_user_bookings(current_user_id()),venue_names=names)


def _detail(booking_id: str, *, preview: dict[str, object] | None = None,
            error: dict[str, str] | None = None, hours: str = "24") -> str:
    details = get_services()[0].booking_details(booking_id)
    success = session.pop("created_booking",None) == booking_id
    return render_template("booking_detail.html",booking=details,preview=preview,error=error,
                           hours=hours,success=success)


@pages.get("/bookings/<booking_id>")
def booking_detail(booking_id: str) -> str:
    """详情显示原始/最终费用及状态；GET 不改变业务记录。"""
    return _detail(booking_id)


@pages.post("/bookings/<booking_id>/cancel-preview")
def cancel_preview(booking_id: str) -> Any:
    """先展示后端退款预览，等待用户明确确认取消。"""
    hours = request.form.get("hours_before_start","")
    try:
        preview = get_services()[1].preview_cancel(booking_id,form_hours(hours))
        return _detail(booking_id,preview=preview,hours=hours)
    except DomainError as error:
        return _detail(booking_id,error=safe_error(error),hours=hours),error_status(error.code)


@pages.post("/bookings/<booking_id>/cancel")
def cancel_booking(booking_id: str) -> Any:
    """确认提交后才取消，GET 请求不会触发取消。"""
    hours = request.form.get("hours_before_start","")
    try:
        get_services()[1].cancel_booking(booking_id,form_hours(hours))
        return redirect(url_for("pages.booking_detail",booking_id=booking_id),303)
    except DomainError as error:
        return _detail(booking_id,error=safe_error(error),hours=hours),error_status(error.code)


@pages.get("/statistics")
def statistics() -> Any:
    """使用服务生成统计，非法 query 保持原值并显示错误。"""
    values = {"start_date":today(),"days":"7","top_n":"5","min_utilization_percent":"50",
              **dict(request.args)}
    report,error,status = None,None,200
    try:
        report = get_services()[2].build_report(**statistics_arguments(values,today()))
    except DomainError as failure:
        error,status = safe_error(failure),error_status(failure.code)
    return render_template("statistics.html",report=report,values=values,error=error),status


@pages.post("/users/switch")
def switch_user() -> Any:
    """保存经 Service 校验的用户到 Session，并刷新本地页面。"""
    user = get_services()[0].get_user(request.form.get("user_id"))
    session["user_id"] = user.user_id
    target = request.form.get("next","/")
    if not target.startswith("/") or target.startswith("//"):
        target = "/"
    return redirect(target,303)


@pages.get("/error")
def error_page() -> str:
    """统一错误页示例。"""
    return render_template("error.html",error=safe_error(DomainError("E_OPERATION_FAILED")))
