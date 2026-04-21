export type StudentAuthProvider =
  | "GOOGLE"
  | "APPLE"
  | "FACEBOOK"
  | "X";

export type StudentAccountStatus =
  | "ACTIVE"
  | "SUSPENDED"
  | "DISABLED";

export type StudentOnboardingStatus =
  | "PENDING"
  | "COMPLETED";

export interface StudentAuthProviderDTO {
  provider: StudentAuthProvider;
  display_label: string;
  enabled: boolean;
}

export interface StudentExamPreferenceCatalogItemDTO {
  id: string;
  exam_key: string;
  visible_label: string;
  description: string | null;
  active: boolean;
  display_order: number;
}

export interface StudentProfileDTO {
  id: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  phone_number_e164: string | null;
  phone_country_code: string;
  phone_is_verified: boolean;
  account_status: StudentAccountStatus;
  onboarding_status: StudentOnboardingStatus;
  onboarding_last_completed_step: number | null;
  profile_image_storage_key: string | null;
  profile_image_url: string | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface StudentSessionTokenResponse {
  access_token: string;
  token_type: string;
}

export interface StudentAuthMeResponse {
  authenticated: boolean;
  profile: StudentProfileDTO;
  provider_links: StudentAuthProvider[];
}

export interface StudentLogoutResponse {
  success: boolean;
  message: string;
}

export interface StudentOnboardingBootstrapDTO {
  provider: StudentAuthProvider;
  provider_email: string | null;
  provider_email_verified: boolean | null;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  provider_avatar_url: string | null;
}

export interface StudentOnboardingStateResponse {
  onboarding_required: boolean;
  onboarding_status: StudentOnboardingStatus;
  last_completed_step: number | null;
  profile: StudentProfileDTO;
  bootstrap: StudentOnboardingBootstrapDTO;
  available_exam_preferences: StudentExamPreferenceCatalogItemDTO[];
}

export interface StudentOnboardingCompleteRequest {
  first_name: string;
  last_name: string;
  display_name: string | null;
  phone_number: string;
  exam_preference_catalog_ids: string[];
  use_provider_avatar: boolean;
}

export interface StudentOnboardingCompleteResponse {
  success: boolean;
  onboarding_status: StudentOnboardingStatus;
  profile: StudentProfileDTO;
}

export interface StudentProfileImageUploadResponse {
  success: boolean;
  profile_image_storage_key: string;
  profile_image_url: string;
}

export interface StudentPhoneValidationRequest {
  phone_number: string;
}

export interface StudentPhoneValidationResponse {
  success: boolean;
  normalized_phone_e164: string;
  phone_country_code: string;
}