"""成员 C：十进制计费；仅在最终金额进行 ROUND_HALF_UP 四舍五入。"""

from decimal import Decimal, ROUND_HALF_UP

from . import config
from .errors import DomainError
from .validation import validate_base_rate, validate_duration, validate_role, validate_start_hour


def round_money(value: Decimal) -> float:
    """把有限十进制金额四舍五入到分，返回用于模型/JSON 的 float。"""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_raw_fee(base_rate: object, duration: object) -> Decimal:
    """计算未加价/折扣的原始费用，供计费和详情展示共用。"""
    return validate_base_rate(base_rate) * validate_duration(duration)


def calculate_fee(base_rate: object, duration: object, start_hour: object, role: object) -> float:
    """计算费率×时长×高峰系数×身份折扣，校验各输入及结束时间。"""
    rate = validate_base_rate(base_rate)
    hours = validate_duration(duration)
    start = validate_start_hour(start_hour)
    identity = validate_role(role)
    if start + hours > config.CLOSE_HOUR:
        raise DomainError("E_OUTSIDE_OPEN_HOURS")
    raw_fee = rate * hours
    peak_multiplier = Decimal(config.PEAK_MULTIPLIER if start >= config.PEAK_START_HOUR
                              else config.NORMAL_MULTIPLIER)
    role_discount = Decimal(config.ROLE_DISCOUNTS[identity])
    final_fee = raw_fee * peak_multiplier * role_discount
    return round_money(final_fee)
