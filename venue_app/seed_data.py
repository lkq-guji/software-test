"""固定演示数据，不使用随机数或当前时间。"""

from .models import User, Venue


def sample_users() -> tuple[User, ...]:
    """返回需求第 16 节的五名用户。"""
    return (User("20260001", "Alice", "student", "active", 0),
            User("20260002", "Bob", "student", "active", 2),
            User("20260003", "Carol", "teacher", "active", 0),
            User("20260004", "Dave", "student", "suspended", 1),
            User("20260005", "Eve", "student", "active", 3))


def sample_venues() -> tuple[Venue, ...]:
    """返回需求第 16 节的三种场馆。"""
    return (Venue("V001", "羽毛球1号场", "badminton", 4, 40),
            Venue("V002", "乒乓球1号台", "table_tennis", 4, 20),
            Venue("V003", "篮球1号场", "basketball", 20, 120))
