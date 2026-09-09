#!/usr/bin/env node
// Node.js 20+，无需 npm 包。仅在服务端或自己的终端中运行。
import { pathToFileURL } from 'node:url';

export function configuration(env = process.env) {
  const key = env.GPTZZZ_API_KEY?.trim();
  const model = env.GPTZZZ_MODEL?.trim();
  if (!key || /[^\x21-\x7e]/.test(key)) throw new Error('请设置有效的 GPTZZZ_API_KEY。');
  if (!model) throw new Error('请从账户复制模型 ID 并设置 GPTZZZ_MODEL。');
  const rawBase = env.GPTZZZ_BASE_URL ?? 'https://gptzzz.ai/v1';
  if (!rawBase || /[\s\x00-\x1f?#]/.test(rawBase)) throw new Error('Base URL 不能包含空白、控制字符、查询参数或片段。');
  let url, decodedPath;
  try { url = new URL(rawBase); decodedPath = decodeURIComponent(url.pathname); }
  catch { throw new Error('GPTZZZ_BASE_URL 不是有效 URL。'); }
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && local)) {
    throw new Error('Base URL 必须使用 HTTPS；本地模拟测试可使用 loopback HTTP。');
  }
  if (url.username || url.password || url.port === '0' || /\/(chat\/completions|models)\/?$/i.test(decodedPath)) {
    throw new Error('Base URL 只能是基础地址，例如 https://gptzzz.ai/v1。');
  }
  return { key, model, base: url.href.replace(/\/+$/, '') };
}

export async function chat(config, prompt, timeoutSeconds = 30) {
  if (!Number.isFinite(timeoutSeconds) || timeoutSeconds <= 0 || timeoutSeconds > 600) {
    throw new Error('timeout 必须为 0 到 600 之间的秒数（不含 0）。');
  }
  if (typeof prompt !== 'string' || !prompt.trim()) throw new Error('prompt 不能为空。');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutSeconds * 1000);
  try {
    const response = await fetch(`${config.base}/chat/completions`, {
      method: 'POST', redirect: 'manual', signal: controller.signal,
      headers: { Authorization: `Bearer ${config.key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: config.model, messages: [{ role: 'user', content: prompt }], stream: false }),
    });
    if (!response.ok) {
      const hints = { 400: '检查模型和请求字段', 401: '检查密钥', 403: '检查账户权限', 404: '检查路径和模型 ID', 422: '检查请求格式', 429: '区分限速与额度不足' };
      throw new Error(`HTTP ${response.status}：${hints[response.status] || '检查服务状态或响应状态；不会自动重试'}。`);
    }
    let data;
    try { data = await response.json(); } catch { throw new Error('响应不是有效 JSON。'); }
    const content = data?.choices?.[0]?.message?.content;
    if (typeof content !== 'string' || !content.trim()) throw new Error('响应没有非空文字内容，检查模型或响应格式。');
    return content;
  } catch (error) {
    if (controller.signal.aborted) throw new Error('请求超时：上游可能已处理，请先核对调用记录再重试。');
    if (error instanceof TypeError) throw new Error('网络请求失败：检查网络、TLS 和基础地址。');
    throw error;
  } finally { clearTimeout(timer); }
}

export async function main(args = process.argv.slice(2)) {
  if (args.includes('--help')) {
    console.log('node scripts/chat.mjs --prompt "用一句话解释 API 中转站" [--timeout 30]');
    return;
  }
  let prompt = '用一句话解释 API 中转站';
  let timeout = 30;
  for (let i = 0; i < args.length; i += 2) {
    if (!['--prompt', '--timeout'].includes(args[i]) || args[i + 1] === undefined) throw new Error('参数不正确，请使用 --help。');
    if (args[i] === '--prompt') prompt = args[i + 1];
    else timeout = Number(args[i + 1]);
  }
  console.log(await chat(configuration(), prompt, timeout));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
