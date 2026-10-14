"""稳定错误码及中文提示；测试优先断言 code。"""

ERROR_MESSAGES = {
    "E_USER_ID_EMPTY": "用户编号不能为空。",
    "E_USER_ID_NON_DIGIT": "用户编号必须是全部由数字组成的字符串。",
    "E_USER_ID_LENGTH": "用户编号长度必须为 8～12 位。",
    "E_DURATION_RANGE": "预约时长必须为 1～4 的整数。",
    "E_PARTICIPANTS_RANGE": "参与人数必须为 1～30 的整数。",
    "E_CAPACITY_RANGE": "场馆容量必须为 1～30 的整数。",
    "E_BASE_RATE_RANGE": "基础费率必须为 10～200 的有限数值。",
    "E_CANCEL_HOURS_RANGE": "提前取消时间必须为 0～168 的有限数值。",
    "E_VIOLATION_COUNT_RANGE": "违规次数必须为 0～5 的整数。",
    "E_DAILY_BOOKING_COUNT_RANGE": "当日已有预约数必须为 0～2 的整数。",
    "E_USER_SUSPENDED": "用户已暂停预约资格。",
    "E_TOO_MANY_VIOLATIONS": "违规次数达到 3 次，不能创建预约。",
    "E_DAILY_BOOKING_LIMIT": "当天已有 2 个有效预约，不能继续预约。",
    "E_OUTSIDE_OPEN_HOURS": "开始时间须为 8～21 的整数，且结束时间不得超过 22 点。",
    "E_CAPACITY_EXCEEDED": "参与人数超过场馆容量。",
    "E_TIME_CONFLICT": "该场馆当天预约时段发生重叠。",
    "E_BOOKING_NOT_FOUND": "预约不存在。",
    "E_BOOKING_NOT_CANCELLABLE": "只有 confirmed 状态的预约可以取消。",
    "E_STAT_DAYS_RANGE": "统计天数必须为 1～31 的整数。",
    "E_TOP_N_RANGE": "Top-N 必须为 1～10 的整数。",
    "E_UTILIZATION_THRESHOLD_RANGE": "使用率阈值必须为 0～100 的整数。",
    "E_DATE_FORMAT": "日期必须为真实日期，格式为 YYYY-MM-DD。",
    "E_ROLE_INVALID": "身份必须为 student 或 teacher。",
    "E_STATUS_INVALID": "用户状态必须为 active 或 suspended。",
    "E_VENUE_TYPE_INVALID": "场馆类型不在支持范围内。",
    "E_USER_NOT_FOUND": "用户不存在。",
    "E_VENUE_NOT_FOUND": "场馆不存在。",
    "E_FEE_RANGE": "费用必须为非负有限数值。",
    "E_DUPLICATE_ID": "记录编号已存在。",
    "E_RECORD_NOT_FOUND": "待更新记录不存在。",
    "E_REPOSITORY_IO": "数据文件无法读取或保存，请检查路径和权限。",
    "E_REPOSITORY_FORMAT": "JSON 数据文件格式错误，请检查数据；原文件未被覆盖。",
    "E_MENU_CHOICE": "请输入菜单编号 1～6。",
}


class DomainError(Exception):
    """带机器可读错误码和中文说明的业务/输入异常。"""

    code: str
    message: str

    def __init__(self, code: str, message: str | None = None) -> None:
        """使用错误码与可选说明创建异常。"""
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "操作失败。")
        super().__init__(f"{self.code}: {self.message}")
