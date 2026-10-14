"""Flask 工厂；注入同一套 Service、Repository 和时钟。"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException

from ..application import Services, create_services
from .. import config as business_config
from ..cli import DEFAULT_DATA_DIR
from ..errors import DomainError
from .presenters import ROLE_LABELS, STATUS_LABELS, TYPE_LABELS, error_status, hour, money, safe_error

ROOT = Path(__file__).resolve().parents[2]


def get_services() -> Services:
    """从当前 Flask app 获取已经装配好的共享服务。"""
    from flask import current_app
    return current_app.extensions["venue_services"]


def today() -> str:
    """读取可注入的本地日期；测试通过 CLOCK 固定时间。"""
    from flask import current_app
    return current_app.config["CLOCK"]().date().isoformat()


def current_user_id() -> str:
    """返回 Session 用户；第一次请求默认选择固定数据首个用户。"""
    if "user_id" not in session:
        users = get_services()[0].list_users()
        if not users:
            raise DomainError("E_USER_NOT_FOUND")
        session["user_id"] = users[0].user_id
    return session["user_id"]


def create_app(config: dict[str, Any] | None = None, *, data_dir: str | Path | None = None,
               services: Services | None = None) -> Flask:
    """创建可测试的 Web 应用；生产入口默认使用与 CLI 相同的 data/。"""
    app = Flask(__name__,template_folder=str(ROOT / "templates"),static_folder=str(ROOT / "static"))
    app.config.update(SECRET_KEY=os.environ.get("VENUE_SECRET_KEY","campus-venue-local-demo"),
                      CLOCK=lambda: datetime.now(timezone(timedelta(hours=8))))
    if config:
        app.config.update(config)
    app.json.ensure_ascii = False
    app.extensions["venue_services"] = services or create_services(data_dir or DEFAULT_DATA_DIR)
    app.extensions["venue_mutation_lock"] = RLock()

    @app.before_request
    def serialize_writes() -> None:
        """串行处理同一 Web 进程的写请求，避免 JSON 读改写交错。"""
        if request.method == "POST":
            app.extensions["venue_mutation_lock"].acquire()
            g.venue_write_locked = True

    @app.teardown_request
    def release_write_lock(error: BaseException | None) -> None:
        """无论请求成功或失败，释放本请求获得的写锁。"""
        if g.pop("venue_write_locked",False):
            app.extensions["venue_mutation_lock"].release()
    from .api import api
    from .routes import pages
    app.register_blueprint(pages)
    app.register_blueprint(api)
    app.jinja_env.filters.update(money=money,hour=hour)

    @app.context_processor
    def shared_context() -> dict[str, object]:
        """导航与中文标签；错误页不因用户数据异常再次失败。"""
        try:
            service = get_services()[0]
            users = service.list_users()
            current = service.get_user(current_user_id())
        except DomainError:
            users,current = [],None
        return dict(test_users=users,current_user=current,status_labels=STATUS_LABELS,
                    role_labels=ROLE_LABELS,type_labels=TYPE_LABELS,limits=business_config,
                    start_hours=[str(value) for value in range(business_config.START_HOUR_RANGE[0],
                                                               business_config.START_HOUR_RANGE[1]+1)])

    @app.errorhandler(DomainError)
    def domain_failure(error: DomainError) -> Any:
        """统一业务错误响应，并保护普通用户不见内部异常。"""
        status = error_status(error.code)
        if request.path.startswith("/api/"):
            return jsonify(success=False,error=safe_error(error)),status
        return render_template("error.html",error=safe_error(error)),status

    @app.errorhandler(Exception)
    def unexpected_failure(error: Exception) -> Any:
        """404/HTTP/服务器异常统一展示，不返回 traceback 或文件路径。"""
        if isinstance(error,HTTPException):
            status = error.code or 500
            code = "E_PAGE_NOT_FOUND" if status == 404 else f"E_HTTP_{status}"
        else:
            app.logger.exception("Web 请求失败")
            status,code = 500,"E_INTERNAL_SERVER_ERROR"
        info = safe_error(DomainError(code))
        if request.path.startswith("/api/"):
            return jsonify(success=False,error=info),status
        return render_template("error.html",error=info),status
    return app
