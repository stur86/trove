/**
 * Shared SSE stream helper for mock API implementations.
 *
 * mockSSELines returns a Promise<Response> that streams the given lines as
 * SSE `data:` events with optional delays, ending with `data: [DONE]`.
 */

export function mockSSELines(lines: string[], lineDelayMs = 80): Promise<Response> {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      await new Promise(r => setTimeout(r, 200)) // initial latency
      for (const line of lines) {
        controller.enqueue(encoder.encode(`data: ${line}\n\n`))
        await new Promise(r => setTimeout(r, lineDelayMs))
      }
      controller.enqueue(encoder.encode('data: [DONE]\n\n'))
      controller.close()
    },
  })
  return Promise.resolve(
    new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
  )
}
