"""API 层的契约实现：会话、请求校验、SSE 事件信封。

本入口只导出可独立验证的契约与会话设施。HTTP 装配单独放在
``api.server``，导入本入口不启动服务或初始化后端。

分工依据 `docs/阶段0-接口草案.md` §4.1–§4.3。

三条不能松的规则：

1. **公开请求不得携带可信字段**，收到即 400 `UNTRUSTED_FIELD`，不做
   "忽略后继续"——静默忽略会掩盖前端 bug，把越权写成正常。
2. **`resume` 是给服务端验证的输入，不是授权凭证**。这里只做结构校验，
   授权事实由服务端 `ChallengeStore` 记录决定。
3. **每个 SSE 事件的 data 都带同一组 `thread_id`/`request_id`/`mode`**，
   页面才能把事件归到同一次请求上。
"""

from api.contracts import (
    ApiError,
    ChatRequest,
    parse_chat_request,
    UNTRUSTED_REQUEST_FIELDS,
    UNTRUSTED_RESUME_FIELDS,
)
from api.events import (
    SSE_EVENTS,
    envelopes,
    format_sse,
)
from api.session import DemoSessionStore, Session

__all__ = [
    "ApiError",
    "ChatRequest",
    "DemoSessionStore",
    "SSE_EVENTS",
    "Session",
    "UNTRUSTED_REQUEST_FIELDS",
    "UNTRUSTED_RESUME_FIELDS",
    "envelopes",
    "format_sse",
    "parse_chat_request",
]
