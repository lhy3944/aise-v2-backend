/**
 * Agent Chat SSE 프록시
 *
 * Next.js rewrites는 SSE 스트림을 버퍼링하므로,
 * Route Handler에서 직접 ReadableStream을 전달하여 토큰 단위 실시간 스트리밍을 보장한다.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8081';

export async function POST(req: Request) {
  const body = await req.json();

  const backendRes = await fetch(`${BACKEND_URL}/api/v1/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok || !backendRes.body) {
    const text = await backendRes.text();
    return new Response(text, { status: backendRes.status });
  }

  return new Response(backendRes.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
