import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE_NAME = "cherukadai_session";
const PROTECTED_PREFIXES = ["/dashboard", "/products"];

/**
 * Route-level gate based on session *presence* only (fast, no backend round-trip).
 * This is a UX convenience, not an authorization decision — every API route
 * independently re-validates the session and the caller's permissions/entitlements.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSessionCookie = request.cookies.has(SESSION_COOKIE_NAME);

  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (isProtected && !hasSessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/products/:path*", "/login", "/setup"],
};
