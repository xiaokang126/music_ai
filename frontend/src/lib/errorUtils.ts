function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function detailToText(detail: unknown): string {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item, index) => `[${index + 1}] ${detailToText(item) || safeJson(item)}`).join('\n');
  }
  if (typeof detail === 'object') {
    const data = detail as Record<string, unknown>;
    const lines: string[] = [];
    const orderedKeys = ['message', 'stage', 'project_id', 'request_id', 'error_type', 'error', 'hint'];
    orderedKeys.forEach((key) => {
      if (data[key] !== undefined && data[key] !== null && data[key] !== '') {
        lines.push(`${key}: ${typeof data[key] === 'object' ? safeJson(data[key]) : String(data[key])}`);
      }
    });
    Object.entries(data).forEach(([key, value]) => {
      if (!orderedKeys.includes(key) && value !== undefined && value !== null && value !== '') {
        lines.push(`${key}: ${typeof value === 'object' ? safeJson(value) : String(value)}`);
      }
    });
    return lines.join('\n') || safeJson(detail);
  }
  return String(detail);
}

export function formatApiError(error: any, fallback = '请求失败', context?: Record<string, unknown>): string {
  const lines: string[] = [fallback];
  if (context && Object.keys(context).length > 0) {
    lines.push(`上下文: ${safeJson(context)}`);
  }

  const config = error?.config || {};
  if (config.method || config.url) {
    lines.push(`请求: ${(config.method || 'GET').toUpperCase()} ${config.baseURL || ''}${config.url || ''}`);
  }

  if (error?.response) {
    const { status, statusText, data } = error.response;
    lines.push(`HTTP状态: ${status}${statusText ? ` ${statusText}` : ''}`);
    if (data?.request_id) lines.push(`request_id: ${data.request_id}`);
    if (data?.path) lines.push(`服务端路径: ${data.path}`);
    const detailText = detailToText(data?.detail);
    if (detailText) lines.push(`服务端错误:\n${detailText}`);
    else if (data) lines.push(`服务端响应:\n${safeJson(data)}`);
  } else if (error?.request) {
    lines.push('网络错误: 请求已发出，但没有收到服务端响应');
    if (error.code) lines.push(`错误代码: ${error.code}`);
    if (error.message) lines.push(`浏览器错误: ${error.message}`);
  } else if (error?.message) {
    lines.push(`客户端错误: ${error.message}`);
  }

  return lines.join('\n');
}

export function recordClientError(context: string, message: string, raw?: unknown) {
  const item = {
    time: new Date().toISOString(),
    context,
    message,
    raw: raw ? safeJson(raw) : '',
  };
  try {
    const key = 'musecut_error_logs';
    const current = JSON.parse(localStorage.getItem(key) || '[]');
    const next = [item, ...(Array.isArray(current) ? current : [])].slice(0, 30);
    localStorage.setItem(key, JSON.stringify(next));
  } catch {
    // localStorage can be unavailable in private modes; console still keeps the trace.
  }
  console.error('[MuseCut error]', item);
}
