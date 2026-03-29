import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { parseGeoSlugFromHost } from "@/lib/geo";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith("/admin") ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/signup")
  ) {
    return NextResponse.next();
  }

  const host = request.headers.get("host");
  const geoSlug = parseGeoSlugFromHost(host);
  const requestHeaders = new Headers(request.headers);
  if (geoSlug) {
    requestHeaders.set("x-cms-geo-slug", geoSlug);
  }
  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
