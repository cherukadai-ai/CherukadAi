import { cookies } from "next/headers";

import { apiClient, ApiError } from "@/lib/api-client";
import type { Session } from "@/lib/auth/types";

const SESSION_COOKIE_NAME = "cherukadai_session";

/**
 * Resolves the current session by forwarding the session cookie to the backend.
 *
 * This never decodes/trusts the cookie itself — the backend is the sole source of
 * truth for who the caller is and what they're entitled to. Returns `null` when
 * unauthenticated, which callers must treat as "no access", not "org user with no
 * permissions".
 *
 * NOTE: the `/me` endpoint is implemented by the `identity` module in a later
 * phase; this helper is wired up now so pages/layouts can be written against a
 * stable contract.
 */
export async function getSession(): Promise<Session> {
  const cookieStore = await cookies();
  if (!cookieStore.has(SESSION_COOKIE_NAME)) {
    return null;
  }

  try {
    return await apiClient.get<Session>("/identity/me", {
      headers: { Cookie: cookieStore.toString() },
    });
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 404)) {
      return null;
    }
    throw error;
  }
}
