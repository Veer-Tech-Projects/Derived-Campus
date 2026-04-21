export type StudentAccountStatusTone = "default" | "success" | "warning";

export interface StudentAccountSummaryViewModel {
  fullName: string;
  displayName: string | null;
  profileImageUrl: string | null;
  providerLabel: string;
  accountStatusLabel: string;
  accountStatusTone: StudentAccountStatusTone;
  onboardingStatusLabel: string;
  onboardingStatusTone: StudentAccountStatusTone;
  email: string | null;
}

export type StudentProfileDetailsViewModel = {
  firstName: string;
  lastName: string;
  displayName: string | null;
};

export interface StudentConnectedIdentityViewModel {
  providerLabel: string;
  email: string | null;
}

export interface StudentContactViewModel {
  phoneNumber: string | null;
  phoneVerificationLabel: string;
  phoneVerificationTone: StudentAccountStatusTone;
}

export interface StudentExamPreferencesViewModel {
  items: string[];
  hasResolvedSelections: boolean;
}