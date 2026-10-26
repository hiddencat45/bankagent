"""演示会话：把 Bearer 令牌换成可信的 ``user_id`` / ``account_id``。

这是**唯一**允许产生可信身份的地方。页面永远拿不到 ``user_id``，只能拿到
一个不可猜测的令牌；服务器每次请求都重新解析。

契约 §4.1 要求「演示会话的发放方式由 A 在首个 API PR 中提供受控入口」，
且「不能让页面硬编码用户或访问令牌」。因此：

* 令牌由 :func:`secrets.token_urlsafe` 生成，不可预测
* 令牌不写入日志、不进 State、不进 SSE
* 会话建立时记录它拥有哪些 ``thread_id``，用于拒绝跨会话访问（404）
"""

import secrets
import threading
from dataclasses import dataclass, field

from bankagent.api.contracts import ApiError

__all__ = ["DemoSessionStore", "Session"]

# 令牌长度：32 字节熵，足够抵抗猜测，也不至于让请求头过长。
_TOKEN_BYTES = 32


@dataclass
class Session:
    """一次已登录的演示会话。"""

    token: str
    user_id: str
    account_id: str
    # 该会话可见的 thread。新建 thread 时登记，用于归属校验。
    threads: set[str] = field(default_factory=set)


class DemoSessionStore:
    """进程内会话表。

    只在本地演示使用：进程重启即丢，且**不是**真实认证。RED 挑战的强认证
    也不能拿这里的会话充当认证结果（契约 §4.3）。
    """

    def __init__(self, *, lock: "threading.RLock | None" = None) -> None:
        self._lock = lock if lock is not None else threading.RLock()
        self._by_token: dict[str, Session] = {}

    # -- 发放 -------------------------------------------------------------

    def issue(self, *, user_id: str, account_id: str) -> Session:
        """为已核实的用户签发一个演示会话。

        调用方（演示入口）负责确认这确实是一个合法演示用户；本方法不做
        权限判断，只负责生成不可预测的令牌。
        """
        if not isinstance(user_id, str) or not user_id:
            raise ApiError("INVALID_REQUEST", "user_id 不能为空。", 400)
        if not isinstance(account_id, str) or not account_id:
            raise ApiError("INVALID_REQUEST", "account_id 不能为空。", 400)

        token = secrets.token_urlsafe(_TOKEN_BYTES)
        session = Session(token=token, user_id=user_id, account_id=account_id)
        with self._lock:
            self._by_token[token] = session
        return session

    # -- 解析与归属 -------------------------------------------------------

    def resolve(self, authorization: str | None) -> Session:
        """从 ``Authorization`` 头解析会话；失败一律 401。

        不在错误信息里区分"令牌不存在"和"格式不对"：那会把令牌空间
        的探测变成可利用的信息泄露。
        """
        token = self._extract_bearer(authorization)
        with self._lock:
            session = self._by_token.get(token)
        if session is None:
            raise ApiError("UNAUTHENTICATED", "登录状态已失效，请重新开始演示。", 401)
        return session

    @staticmethod
    def _extract_bearer(authorization: str | None) -> str:
        if not isinstance(authorization, str):
            raise ApiError("UNAUTHENTICATED", "缺少登录凭证。", 401)
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise ApiError("UNAUTHENTICATED", "登录凭证格式不正确。", 401)
        return token.strip()

    # -- thread 归属 ------------------------------------------------------

    def register_thread(self, session: Session, thread_id: str) -> None:
        """登记一个属于该会话的 thread。"""
        with self._lock:
            stored = self._by_token.get(session.token)
            if stored is None:
                raise ApiError("UNAUTHENTICATED", "登录状态已失效。", 401)
            stored.threads.add(thread_id)
            session.threads.add(thread_id)

    def require_thread(self, session: Session, thread_id: str) -> None:
        """确认 thread 属于当前会话，否则 404。

        用 404 而不是 403：不让攻击者通过状态码区分"这个 thread 存在但
        不是你的"和"这个 thread 不存在"。
        """
        with self._lock:
            stored = self._by_token.get(session.token)
            owns = stored is not None and thread_id in stored.threads
        if not owns:
            raise ApiError("THREAD_NOT_FOUND", "会话不存在或已失效。", 404)

    # -- 失效 -------------------------------------------------------------

    def invalidate_all(self) -> None:
        """使全部会话失效（``POST /demo/reset`` 用）。

        重置必须同时清掉会话、图 Checkpoint、挑战与授权，否则旧确认卡
        还能继续扣款（契约 §3.5）。
        """
        with self._lock:
            self._by_token.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._by_token)
