// 浏览器与 Node 共用，无第三方依赖；只实现已确认的聊天请求和 SSE 信封。
const EVENTS = new Set(['status', 'message', 'card', 'interrupt', 'error', 'done']);
const STATUSES = new Set(['PROCESSING', 'NEEDS_CLARIFICATION', 'AWAITING_CONFIRMATION',
  'AWAITING_AUTHENTICATION', 'COMPLETED', 'REJECTED', 'FAILED', 'PENDING']);
const MAX_FRAME_LENGTH = 1024 * 1024;
const nonempty = value => typeof value === 'string' && value.trim().length > 0;

export class AgentClientError extends Error {
  constructor(code, message) { super(message); this.name = 'AgentClientError'; this.code = code; }
}
const protocolError = () => new AgentClientError('INVALID_STREAM', '服务返回的数据不完整或格式有误。');

function parseFrame(lines) {
  let event = 'message';
  const data = [];
  for (const line of lines) {
    if (line.startsWith(':')) continue;
    const colon = line.indexOf(':');
    const key = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (key === 'event') event = value;
    if (key === 'data') data.push(value);
  }
  if (!data.length) return null;
  if (!EVENTS.has(event)) throw protocolError();
  let payload;
  try { payload = JSON.parse(data.join('\n')); } catch { throw protocolError(); }
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)
      || !nonempty(payload.thread_id) || !nonempty(payload.request_id)
      || !['offline', 'model'].includes(payload.mode)) throw protocolError();
  if (['status', 'done'].includes(event) && !STATUSES.has(payload.status)) throw protocolError();
  return { event, data: payload };
}

/** 按字节增量读取，完整信封才交给页面；done 表示本轮流结束，不代表成功。 */
export async function readAgentStream(body, onEvent) {
  if (!body?.getReader || typeof onEvent !== 'function') throw protocolError();
  const reader = body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '', lines = [], frameLength = 0, envelope, finished = false;
  const consume = final => {
    while (buffer.length) {
      const match = /\r\n|\r|\n/.exec(buffer);
      if (!match || (!final && match[0] === '\r' && match.index === buffer.length - 1)) break;
      const line = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);
      frameLength += line.length + 1;
      if (frameLength > MAX_FRAME_LENGTH) throw protocolError();
      if (line) { lines.push(line); continue; }
      const frame = parseFrame(lines);
      lines = []; frameLength = 0;
      if (!frame) continue;
      if (finished) throw protocolError();
      if (!envelope) {
        if (frame.event !== 'status') throw protocolError();
        envelope = { ...frame.data };
      }
      if (['thread_id', 'request_id', 'mode'].some(key => frame.data[key] !== envelope[key])) {
        throw protocolError();
      }
      if (frame.event === 'done') {
        if (frame.data.status === 'PROCESSING') throw protocolError();
        finished = true;
      }
      onEvent(frame);
    }
    if (buffer.length + frameLength > MAX_FRAME_LENGTH) throw protocolError();
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      consume(done);
      if (done) break;
    }
    if (buffer.length || lines.some(line => !line.startsWith(':'))) throw protocolError();
    if (!finished) {
      throw new AgentClientError('STREAM_INTERRUPTED', '连接已中断，办理结果尚未确认；请核对状态，勿重复提交。');
    }
  } catch (error) {
    await reader.cancel().catch(() => {});
    if (error instanceof AgentClientError) throw error;
    throw new AgentClientError('STREAM_INTERRUPTED', '连接已中断，请核对办理状态；不会自动重新提交。');
  } finally { reader.releaseLock(); }
}

function chatBody(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)
      || Object.keys(input).some(key => !['thread_id', 'message', 'resume'].includes(key))) {
    throw new AgentClientError('INVALID_REQUEST', '请求只能包含会话引用、消息或恢复信息。');
  }
  const { thread_id = null, message = null, resume = null } = input;
  if (thread_id !== null && !nonempty(thread_id)) {
    throw new AgentClientError('INVALID_REQUEST', '会话引用无效。');
  }
  if (resume === null) {
    if (!nonempty(message)) throw new AgentClientError('INVALID_REQUEST', '请输入要办理的业务。');
    return { thread_id, message, resume: null };
  }
  if (message !== null || !nonempty(thread_id) || typeof resume !== 'object'
      || Array.isArray(resume) || !nonempty(resume.challenge_id)
      || !['approve', 'reject'].includes(resume.decision)
      || Object.keys(resume).some(key => !['challenge_id', 'decision', 'otp'].includes(key))
      || (resume.otp != null && typeof resume.otp !== 'string')) {
    throw new AgentClientError('INVALID_REQUEST', '确认请求有误，请核对当前确认卡。');
  }
  return { thread_id, message: null, resume: { ...resume } };
}

/** 同一客户端实例一次只发一个 POST。令牌由服务端会话入口提供，不持久化。 */
export function createAgentClient({ fetchImpl = globalThis.fetch } = {}) {
  let busy = false;
  return {
    get busy() { return busy; },
    async send(input, { token, onEvent, signal } = {}) {
      if (busy) throw new AgentClientError('RUN_BUSY', '正在处理上一条请求，请等待结果。');
      if (!nonempty(token)) throw new AgentClientError('UNAUTHENTICATED', '请先建立演示会话。');
      if (typeof onEvent !== 'function') throw new TypeError('onEvent is required');
      const payload = chatBody(input);
      busy = true;
      try {
        const response = await fetchImpl('/agent/chat', {
          method: 'POST', credentials: 'same-origin', cache: 'no-store', signal,
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream',
            Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          let error;
          try { error = await response.json(); } catch { /* 不显示原始响应或堆栈。 */ }
          const code = nonempty(error?.code) ? error.code : `HTTP_${response.status}`;
          throw new AgentClientError(code, '服务未接受请求，请检查会话或稍后重试。');
        }
        if (response.headers.get('content-type')?.split(';')[0].trim() !== 'text/event-stream') {
          await response.body?.cancel();
          throw protocolError();
        }
        await readAgentStream(response.body, frame => {
          if (payload.thread_id && payload.thread_id !== frame.data.thread_id) throw protocolError();
          onEvent(frame);
        });
      } catch (error) {
        if (error instanceof AgentClientError) throw error;
        throw new AgentClientError('CONNECTION_FAILED', '连接失败，办理状态尚未确认；不会自动重新提交。');
      } finally { busy = false; }
    },
  };
}
