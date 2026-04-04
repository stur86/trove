/**
 * Base HTTP client for the Trove API.
 *
 * All requests go to /api (proxied to FastAPI in dev, served directly in prod).
 * Throws an Error with a descriptive message on non-2xx responses.
 */

const BASE = '/api'

/**
 * Make a GET request and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path (e.g. "/config")
 * @param headers Optional additional request headers
 */
export async function get<T>(path: string, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a PUT request with a JSON body and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path
 * @param body Request body (serialised to JSON)
 * @param headers Optional additional request headers
 */
export async function put<T>(path: string, body: unknown, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(headers as Record<string, string> ?? {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a POST request with an optional JSON body. Returns the raw Response for SSE streaming.
 * Throws if the response is non-2xx.
 * @param path API path
 * @param body Optional request body
 * @param headers Optional additional request headers
 */
export async function post(path: string, body?: unknown, headers?: HeadersInit): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(headers as Record<string, string> ?? {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res
}

/** Encode credentials for HTTP Basic Authorization header. */
export function basicAuth(username: string, password: string): string {
  return `Basic ${btoa(`${username}:${password}`)}`
}
