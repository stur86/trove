/**
 * Per-session token management for the Trove frontend.
 *
 * The token is held in module-level JS memory (not localStorage / sessionStorage).
 * It is invisible to other origins, protecting against cross-origin request forgery.
 * On page reload a fresh token is fetched automatically by App.tsx.
 */

let _sessionToken: string | null = null

/**
 * Fetch a session token from the server and store it in module memory.
 *
 * Must be called before any other API request. Called once at app init by App.tsx.
 * Also called by the API client on 401 retry.
 */
export async function fetchSession(): Promise<void> {
  const res = await fetch('/api/session')
  if (!res.ok) throw new Error(`Session initialisation failed: ${res.status}`)
  const { token } = (await res.json()) as { token: string }
  _sessionToken = token
}

/** Return the current in-memory session token, or null if not yet fetched. */
export function getSessionToken(): string | null {
  return _sessionToken
}
