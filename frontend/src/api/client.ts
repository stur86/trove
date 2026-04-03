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
 */
export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a PUT request with a JSON body and return the parsed JSON response.
 * @template T Expected response type
 */
export async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a POST request and return the raw Response (for SSE streaming).
 * Throws if the request itself fails (non-2xx status).
 */
export async function post(path: string): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res
}
