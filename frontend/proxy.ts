import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";

function matchesPath(pathname: string, targetPath: string): boolean {
  return pathname === targetPath || pathname.startsWith(`${targetPath}/`);
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  const isLoginRoute = matchesPath(pathname, studentAuthRouteConfig.loginPath);
  const isOnboardingRoute = matchesPath(
    pathname,
    studentAuthRouteConfig.onboardingPath,
  );
  const isPostLoginRoute = matchesPath(
    pathname,
    studentAuthRouteConfig.postLoginPath,
  );

  const isStudentAccountRoute = matchesPath(pathname, "/student-account");

  const isProtectedStudentRoute =
    isOnboardingRoute || isPostLoginRoute || isStudentAccountRoute;

  const refreshCookie = request.cookies.get(
    studentAuthRouteConfig.refreshCookieName,
  );
  const hasStudentRefreshCookie = Boolean(refreshCookie?.value);

  if (isProtectedStudentRoute && !hasStudentRefreshCookie) {
    const loginUrl = new URL(studentAuthRouteConfig.loginPath, request.url);

    if (pathname !== studentAuthRouteConfig.loginPath) {
      loginUrl.searchParams.set("next", `${pathname}${search}`);
    }

    return NextResponse.redirect(loginUrl);
  }

  if (isLoginRoute && hasStudentRefreshCookie) {
    const destinationUrl = new URL(
      studentAuthRouteConfig.postLoginPath,
      request.url,
    );
    return NextResponse.redirect(destinationUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
};