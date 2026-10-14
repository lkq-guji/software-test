"""纯显示转换、HTTP 状态和字段错误映射，不实现业务算法。"""

from ..errors import DomainError, ERROR_MESSAGES

STATUS_LABELS = {"confirmed":"已确认", "cancelled":"已取消", "completed":"已完成", "no_show":"未到场"}
ROLE_LABELS = {"student":"学生", "teacher":"教师"}
TYPE_LABELS = {"badminton":"羽毛球", "table_tennis":"乒乓球", "basketball":"篮球"}
ERROR_FIELDS = {
    "E_USER_ID_EMPTY":"user_id", "E_USER_ID_NON_DIGIT":"user_id", "E_USER_ID_LENGTH":"user_id",
    "E_USER_NOT_FOUND":"user_id", "E_USER_SUSPENDED":"user_id", "E_TOO_MANY_VIOLATIONS":"user_id",
    "E_DAILY_BOOKING_LIMIT":"user_id", "E_DATE_FORMAT":"date", "E_DURATION_RANGE":"duration",
    "E_PARTICIPANTS_RANGE":"participants", "E_CAPACITY_EXCEEDED":"participants",
    "E_OUTSIDE_OPEN_HOURS":"start_hour", "E_TIME_CONFLICT":"start_hour",
    "E_VENUE_NOT_FOUND":"venue_id", "E_BASE_RATE_RANGE":"venue_id",
    "E_CANCEL_HOURS_RANGE":"hours_before_start", "E_STAT_DAYS_RANGE":"days",
    "E_TOP_N_RANGE":"top_n", "E_UTILIZATION_THRESHOLD_RANGE":"min_utilization_percent",
}
CONFLICT_CODES = frozenset({"E_TIME_CONFLICT", "E_USER_SUSPENDED", "E_TOO_MANY_VIOLATIONS",
                           "E_DAILY_BOOKING_LIMIT", "E_BOOKING_NOT_CANCELLABLE", "E_DUPLICATE_ID"})
NOT_FOUND_CODES = frozenset({"E_USER_NOT_FOUND", "E_VENUE_NOT_FOUND", "E_BOOKING_NOT_FOUND", "E_PAGE_NOT_FOUND"})
WEB_MESSAGES = {"E_REQUEST_FORMAT":"请求格式错误，请提交有效的 JSON 对象及字段。",
                "E_PAGE_NOT_FOUND":"页面或接口不存在，请检查地址。",
                "E_INTERNAL_SERVER_ERROR":"操作失败，请检查输入或联系管理员。"}


def money(value: float) -> str:
    """将后端金额格式化为 ¥XX.XX。"""
    return f"¥{value:.2f}"


def hour(value: int) -> str:
    """将整数小时显示为 HH:00。"""
    return f"{value:02d}:00"


def safe_error(error: DomainError) -> dict[str, str]:
    """保留错误码，未知说明使用通用中文文本，避免内部路径泄露。"""
    return {"code": error.code,
            "message": ERROR_MESSAGES.get(error.code,WEB_MESSAGES.get(error.code,"操作失败，请检查输入或联系管理员。")),
            "field": ERROR_FIELDS.get(error.code,"operation")}


def error_status(code: str) -> int:
    """把领域错误映射到一致 HTTP 状态。"""
    if code in NOT_FOUND_CODES:
        return 404
    if code in CONFLICT_CODES:
        return 409
    if code in {"E_REPOSITORY_IO", "E_REPOSITORY_FORMAT", "E_INTERNAL_SERVER_ERROR"}:
        return 500
    return 400
