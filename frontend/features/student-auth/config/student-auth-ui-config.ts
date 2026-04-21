function requireEnv(value: string | undefined, name: string): string {
  if (!value || !value.trim()) {
    throw new Error(`${name} is not configured in the environment.`);
  }
  return value.trim();
}

function requirePositiveIntegerEnv(
  value: string | undefined,
  name: string,
): number {
  const normalized = requireEnv(value, name);
  const parsed = Number(normalized);

  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${name} must be a positive integer.`);
  }

  return parsed;
}

function requireMimeTypeListEnv(
  value: string | undefined,
  name: string,
): string[] {
  const normalized = requireEnv(value, name);
  const items = normalized
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);

  if (items.length === 0) {
    throw new Error(`${name} must contain at least one mime type.`);
  }

  return items;
}

export const studentAuthUiConfig = Object.freeze({
  profileImageMaxBytes: requirePositiveIntegerEnv(
    process.env.NEXT_PUBLIC_STUDENT_PROFILE_IMAGE_MAX_BYTES,
    "NEXT_PUBLIC_STUDENT_PROFILE_IMAGE_MAX_BYTES",
  ),
  profileImageAllowedMimeTypes: requireMimeTypeListEnv(
    process.env.NEXT_PUBLIC_STUDENT_PROFILE_IMAGE_ALLOWED_MIME_TYPES,
    "NEXT_PUBLIC_STUDENT_PROFILE_IMAGE_ALLOWED_MIME_TYPES",
  ),
});