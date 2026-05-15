/**
 * Base HTTP client for the Trove API.
 *
 * All requests go to /api (proxied to FastAPI in dev, served directly in prod).
 * Injects the X-Trove-Session header on every request and retries once on 401
 * (session expired) by re-fetching the token via fetchSession().
 * Throws an Error with a descriptive message on non-2xx responses after retry.
 */

import { fetchSession, getSessionToken } from './session'

const BASE = '/api'

/**
 * Error thrown by all API helpers on a non-2xx response.
 * Carries the HTTP status code so callers can handle specific cases
 * (e.g. 503 → model not ready) without parsing the error message string.
 */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Central fetch wrapper: injects the session token and handles 401 retry.
 *
 * On a 401 response, calls fetchSession() to obtain a fresh token and retries
 * the original request exactly once. If the retry also fails, the Response is
 * returned as-is (callers decide whether to throw).
 *
 * @param url Full URL (BASE + path already joined by callers)
 * @param init Standard RequestInit — credentials: 'include' is added automatically
 */
async function apiRequest(url: string, init: RequestInit): Promise<Response> {
  const buildHeaders = (): Headers => {
    const h = new Headers(init.headers as HeadersInit | undefined)
    const token = getSessionToken()
    if (token) h.set('X-Trove-Session', token)
    return h
  }

  const res = await fetch(url, { ...init, headers: buildHeaders(), credentials: 'include' })
  if (res.status === 401) {
    // Session expired or not yet initialised — refresh and retry once.
    await fetchSession()
    return fetch(url, { ...init, headers: buildHeaders(), credentials: 'include' })
  }
  return res
}

/**
 * Make a GET request and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path (e.g. "/config")
 * @param headers Optional additional request headers
 */
export async function get<T>(path: string, headers?: HeadersInit): Promise<T> {
  const res = await apiRequest(`${BASE}${path}`, { headers: headers as Record<string, string> ?? {} })
  if (!res.ok) throw new ApiError(res.status, `GET ${path} failed: ${res.status}`)
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
  const res = await apiRequest(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...(headers as Record<string, string> ?? {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new ApiError(res.status, `PUT ${path} failed: ${res.status}`)
  return res.json()
}

/**
 * Make a POST request with an optional JSON body. Returns the raw Response for SSE streaming.
 * Throws if the response is non-2xx after retry.
 * @param path API path
 * @param body Optional request body
 * @param headers Optional additional request headers
 */
export async function post(path: string, body?: unknown, headers?: HeadersInit): Promise<Response> {
  const res = await apiRequest(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(headers as Record<string, string> ?? {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new ApiError(res.status, `POST ${path} failed: ${res.status}`)
  return res
}

/**
 * Make a PATCH request with a JSON body and return the parsed JSON response.
 * @template T Expected response type
 * @param path API path
 * @param body Request body (serialised to JSON)
 * @param headers Optional additional request headers
 */
export async function patch<T>(path: string, body: unknown, headers?: HeadersInit): Promise<T> {
  const res = await apiRequest(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...(headers as Record<string, string> ?? {}) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new ApiError(res.status, `PATCH ${path} failed: ${res.status}`)
  return res.json()
}

/** Encode credentials for HTTP Basic Authorization header. */
export function basicAuth(username: string, password: string): string {
  return `Basic ${btoa(`${username}:${password}`)}`
}

/**
 * Make a DELETE request. Returns void on 204, throws on error.
 * @param path API path
 * @param headers Optional additional request headers
 */
export async function del(path: string, headers?: HeadersInit): Promise<void> {
  const res = await apiRequest(`${BASE}${path}`, {
    method: 'DELETE',
    headers: headers as Record<string, string> ?? {},
  })
  if (!res.ok) throw new ApiError(res.status, `DELETE ${path} failed: ${res.status}`)
}

/**
 * Make a GET request and return the response as a Blob (for file downloads).
 * Handles session injection and 401 retry identically to get().
 * @param path API path (e.g. "/app/admin/bundle/export")
 */
export async function getBlob(path: string): Promise<Blob> {
  const res = await apiRequest(`${BASE}${path}`, {})
  if (!res.ok) throw new ApiError(res.status, `GET ${path} failed: ${res.status}`)
  return res.blob()
}

/**
 * Make a POST request with a FormData body (for multipart file uploads).
 * Does NOT set Content-Type — the browser sets it automatically with the boundary.
 * @param path API path
 * @param form FormData to send
 */
export async function postFormData(path: string, form: FormData): Promise<Response> {
  const res = await apiRequest(`${BASE}${path}`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new ApiError(res.status, `POST ${path} failed: ${res.status}`)
  return res
}
