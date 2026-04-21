function requireEnv(value: string | undefined, name: string): string {
  if (!value || !value.trim()) {
    throw new Error(`${name} is not configured in the environment.`);
  }
  return value.trim();
}

function requirePathEnv(value: string | undefined, name: string): string {
  const path = requireEnv(value, name);
  if (!path.startsWith("/")) {
    throw new Error(`${name} must start with '/'.`);
  }
  return path;
}

export const studentAuthRouteConfig = Object.freeze({
  refreshCookieName: requireEnv(
    process.env.NEXT_PUBLIC_STUDENT_REFRESH_COOKIE_NAME,
    "NEXT_PUBLIC_STUDENT_REFRESH_COOKIE_NAME"
  ),
  loginPath: requirePathEnv(
    process.env.NEXT_PUBLIC_STUDENT_LOGIN_PATH,
    "NEXT_PUBLIC_STUDENT_LOGIN_PATH"
  ),
  onboardingPath: requirePathEnv(
    process.env.NEXT_PUBLIC_STUDENT_ONBOARDING_PATH,
    "NEXT_PUBLIC_STUDENT_ONBOARDING_PATH"
  ),
  postLoginPath: requirePathEnv(
    process.env.NEXT_PUBLIC_STUDENT_POST_LOGIN_PATH,
    "NEXT_PUBLIC_STUDENT_POST_LOGIN_PATH"
  ),
});