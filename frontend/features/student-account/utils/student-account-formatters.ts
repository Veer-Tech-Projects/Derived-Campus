import type {
  StudentAccountSummaryViewModel,
  StudentConnectedIdentityViewModel,
  StudentContactViewModel,
  StudentExamPreferencesViewModel,
  StudentProfileDetailsViewModel,
} from "../types/student-account-view-models";
import type { StudentProfileDTO } from "@/features/student-auth/types/student-auth-contracts";

function formatProviderLabel(provider: string | null | undefined): string {
  const normalized = (provider ?? "").trim().toUpperCase();

  if (normalized === "GOOGLE") {
    return "Google";
  }

  if (!normalized) {
    return "Connected provider";
  }

  return normalized;
}

function formatAccountStatusLabel(status: string | null | undefined): string {
  const normalized = (status ?? "").trim().toUpperCase();

  if (normalized === "ACTIVE") {
    return "Active";
  }

  if (normalized === "SUSPENDED") {
    return "Suspended";
  }

  if (normalized === "DISABLED") {
    return "Disabled";
  }

  return "Unknown";
}

function formatOnboardingStatusLabel(status: string | null | undefined): string {
  const normalized = (status ?? "").trim().toUpperCase();

  if (normalized === "COMPLETED") {
    return "Onboarding complete";
  }

  if (normalized === "PENDING") {
    return "Onboarding pending";
  }

  return "Unknown";
}

function resolveStatusTone(
  status: string | null | undefined,
): "default" | "success" | "warning" {
  const normalized = (status ?? "").trim().toUpperCase();

  if (normalized === "ACTIVE" || normalized === "COMPLETED" || normalized === "VERIFIED") {
    return "success";
  }

  if (normalized === "SUSPENDED" || normalized === "PENDING") {
    return "warning";
  }

  return "default";
}

export function buildStudentFullName(profile: StudentProfileDTO): string {
  const displayName = profile.display_name?.trim() || "";

  if (displayName) {
    return displayName;
  }

  const fullName = [profile.first_name ?? "", profile.last_name ?? ""]
    .join(" ")
    .trim();

  if (fullName) {
    return fullName;
  }

  return "Student";
}

export function buildStudentAccountSummaryViewModel(args: {
  profile: StudentProfileDTO;
  providerLabel?: string | null;
  email?: string | null;
}): StudentAccountSummaryViewModel {
  const { profile, providerLabel, email = null } = args;

  return {
    fullName: buildStudentFullName(profile),
    displayName: profile.display_name?.trim() || null,
    profileImageUrl: profile.profile_image_url,
    providerLabel: formatProviderLabel(providerLabel),
    accountStatusLabel: formatAccountStatusLabel(profile.account_status),
    accountStatusTone: resolveStatusTone(profile.account_status),
    onboardingStatusLabel: formatOnboardingStatusLabel(profile.onboarding_status),
    onboardingStatusTone: resolveStatusTone(profile.onboarding_status),
    email,
  };
}

export function buildStudentProfileDetailsViewModel(
  profile: StudentProfileDTO,
): StudentProfileDetailsViewModel {
  return {
    firstName: profile.first_name?.trim() || "",
    lastName: profile.last_name?.trim() || "",
    displayName: profile.display_name?.trim() || null,
  };
}

export function buildStudentConnectedIdentityViewModel(args: {
  providerLabel?: string | null;
  email?: string | null;
}): StudentConnectedIdentityViewModel {
  return {
    providerLabel: formatProviderLabel(args.providerLabel),
    email: args.email?.trim() || null,
  };
}

export function formatPhoneNumberForDisplay(value: string | null | undefined): string | null {
  const normalized = (value ?? "").trim();

  if (!normalized) {
    return null;
  }

  if (!normalized.startsWith("+91")) {
    return normalized;
  }

  const digits = normalized.slice(3);
  if (digits.length !== 10) {
    return normalized;
  }

  return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
}

export function buildStudentContactViewModel(
  profile: StudentProfileDTO,
): StudentContactViewModel {
  return {
    phoneNumber: formatPhoneNumberForDisplay(profile.phone_number_e164),
    phoneVerificationLabel: profile.phone_is_verified ? "Verified" : "Not verified",
    phoneVerificationTone: profile.phone_is_verified ? "success" : "warning",
  };
}

export function buildStudentExamPreferencesViewModel(
  labels: string[] | null | undefined,
): StudentExamPreferencesViewModel {
  const normalized = (labels ?? []).map((item) => item.trim()).filter(Boolean);

  return {
    items: normalized,
    hasResolvedSelections: normalized.length > 0,
  };
}