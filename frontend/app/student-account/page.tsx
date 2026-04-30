"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Area } from "react-easy-crop";

import { getStudentOnboardingState } from "@/features/student-auth/api/student-auth-api";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";
import { studentAuthUiConfig } from "@/features/student-auth/config/student-auth-ui-config";
import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import { StudentAccountShell } from "@/features/student-account/components/student-account-shell";
import { StudentAccountHeader } from "@/features/student-account/components/student-account-header";
import { StudentProfileSummaryCard } from "@/features/student-account/components/student-profile-summary-card";
import { StudentProfileImageSection } from "@/features/student-account/components/student-profile-image-section";
import { StudentProfileDetailsSection } from "@/features/student-account/components/student-profile-details-section";
import { StudentConnectedIdentitySection } from "@/features/student-account/components/student-connected-identity-section";
import { StudentContactSection } from "@/features/student-account/components/student-contact-section";
import { StudentExamPreferencesSection } from "@/features/student-account/components/student-exam-preferences-section";
import { StudentAccountActions } from "@/features/student-account/components/student-account-actions";
import { StudentAccountProfileImageEditor } from "@/features/student-account/components/student-account-profile-image-editor";
import { useStudentAccountProfileImage } from "@/features/student-account/hooks/use-student-account-profile-image";
import {
  buildStudentAccountSummaryViewModel,
  buildStudentConnectedIdentityViewModel,
  buildStudentContactViewModel,
  buildStudentProfileDetailsViewModel,
} from "@/features/student-account/utils/student-account-formatters";
import type { StudentOnboardingStateResponse } from "@/features/student-auth/types/student-auth-contracts";
import { useStudentAccountProfileForm } from "@/features/student-account/hooks/use-student-account-profile-form";
import { useStudentAccountExamPreferencesForm } from "@/features/student-account/hooks/use-student-account-exam-preferences-form";
import { useStudentAccountPhoneForm } from "@/features/student-account/hooks/use-student-account-phone-form";
import { useStudentBillingOverview } from "@/features/student-billing/hooks/use-student-billing-overview";
import { StudentAccountBillingLauncher } from "@/features/student-billing/components/student-account-billing-launcher";
import type { StudentAvailableCreditsBadgeViewModel } from "@/features/student-billing/types/student-billing-view-models";

type TabState = "profile" | "account" | "preferences" | "billing";

const ACCOUNT_TABS: Array<{ id: TabState; label: string }> = [
  { id: "profile", label: "Profile" },
  { id: "account", label: "Account" },
  { id: "preferences", label: "Preferences" },
  { id: "billing", label: "Billing" },
];

export default function StudentAccountPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    status,
    profile,
    providerLinks,
    accessToken,
    refreshSession,
    logout,
  } = useStudentAuth();

  const [loggingOut, setLoggingOut] = useState(false);
  const requestedTab = searchParams.get("tab");
  const initialTab: TabState =
    requestedTab === "billing" ? "billing" : "profile";

  const [activeTab, setActiveTab] = useState<TabState>(initialTab);

  useEffect(() => {
    if (requestedTab === "billing") {
      setActiveTab("billing");
      return;
    }

    if (requestedTab === "profile") {
      setActiveTab("profile");
      return;
    }

    if (requestedTab === "account") {
      setActiveTab("account");
      return;
    }

    if (requestedTab === "preferences") {
      setActiveTab("preferences");
    }
  }, [requestedTab]);

  const [identityState, setIdentityState] = useState<{
    loading: boolean;
    providerEmail: string | null;
  }>({
    loading: false,
    providerEmail: null,
  });

  const profileImageFlow = useStudentAccountProfileImage();

  const profileForm = useStudentAccountProfileForm({
    accessToken,
    profile,
    refreshSession,
  });

  const examPreferencesForm = useStudentAccountExamPreferencesForm({
    accessToken,
  });

  const phoneForm = useStudentAccountPhoneForm({
    accessToken,
    profile,
    refreshSession,
  });

  const billingOverviewQuery = useStudentBillingOverview({
    accessToken,
    enabled: status === "authenticated_completed" && Boolean(accessToken),
  });

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(studentAuthRouteConfig.loginPath);
      return;
    }

    if (status === "authenticated_pending_onboarding") {
      router.replace(studentAuthRouteConfig.onboardingPath);
      return;
    }
  }, [router, status]);

  useEffect(() => {
    if (status !== "authenticated_completed" || !accessToken) {
      return;
    }

    const validatedAccessToken = accessToken;
    let cancelled = false;

    async function loadIdentityState() {
      setIdentityState({
        loading: true,
        providerEmail: null,
      });

      try {
        const response: StudentOnboardingStateResponse =
          await getStudentOnboardingState(validatedAccessToken);

        if (cancelled) {
          return;
        }

        setIdentityState({
          loading: false,
          providerEmail: response.bootstrap.provider_email ?? null,
        });
      } catch {
        if (cancelled) {
          return;
        }

        setIdentityState({
          loading: false,
          providerEmail: null,
        });
      }
    }

    void loadIdentityState();

    return () => {
      cancelled = true;
    };
  }, [accessToken, status]);

  async function handleLogout() {
    try {
      setLoggingOut(true);
      await logout();
    } finally {
      setLoggingOut(false);
    }
  }

  const summary = useMemo(() => {
    if (!profile) {
      return null;
    }

    const baseSummary = buildStudentAccountSummaryViewModel({
      profile,
      providerLabel: providerLinks[0] ?? null,
      email: identityState.providerEmail,
    });

    return {
      ...baseSummary,
      profileImageUrl: profileImageFlow.currentProfileImageUrl,
    };
  }, [
    profile,
    providerLinks,
    identityState.providerEmail,
    profileImageFlow.currentProfileImageUrl,
  ]);

  const details = useMemo(() => {
    return profile ? buildStudentProfileDetailsViewModel(profile) : null;
  }, [profile]);

  const connectedIdentity = useMemo(() => {
    return buildStudentConnectedIdentityViewModel({
      providerLabel: providerLinks[0] ?? null,
      email: identityState.providerEmail,
    });
  }, [providerLinks, identityState.providerEmail]);

  const contact = useMemo(() => {
    return profile ? buildStudentContactViewModel(profile) : null;
  }, [profile]);

  const billingGatewayBadgeViewModel =
    useMemo<StudentAvailableCreditsBadgeViewModel | null>(() => {
      if (!billingOverviewQuery.viewModel) {
        return null;
      }

      return {
        availableCredits: billingOverviewQuery.viewModel.wallet.available_credits,
        lowCreditState: billingOverviewQuery.viewModel.lowCreditState,
      };
    }, [billingOverviewQuery.viewModel]);

  if (status === "unknown" || (status === "refreshing" && !profile)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (
    status === "unauthenticated" ||
    status === "authenticated_pending_onboarding"
  ) {
    return null;
  }

  if (!profile || !summary || !details || !contact) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-muted-foreground">Unable to load account data.</p>
      </div>
    );
  }

  return (
    <>
      <StudentAccountShell
        topBar={
          <StudentAccountHeader
            title="Student account"
            onLogout={handleLogout}
            loggingOut={loggingOut}
          />
        }
        hero={<StudentProfileSummaryCard summary={summary} />}
      >
        <div className="mx-auto max-w-2xl">
          <div className="mb-8 flex items-center justify-center gap-8 border-b border-border/40 px-4">
            {ACCOUNT_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`relative pb-3 text-sm font-bold tracking-wide transition-colors ${
                  activeTab === tab.id
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab.label}
                {activeTab === tab.id ? (
                  <div className="absolute bottom-0 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-primary" />
                ) : null}
              </button>
            ))}
          </div>

          <div className="space-y-6">
            {activeTab === "profile" ? (
              <>
                <StudentProfileImageSection
                  profileImageUrl={profileImageFlow.currentProfileImageUrl}
                  canEditUploadedAvatar={profileImageFlow.canEditUploadedAvatar}
                  disabled={profileImageFlow.uploadState.uploading}
                  errorMessage={profileImageFlow.uploadState.errorMessage}
                  fileInputRef={profileImageFlow.fileInputRef}
                  accept={studentAuthUiConfig.profileImageAllowedMimeTypes.join(",")}
                  onFileChange={profileImageFlow.handleImageFileSelection}
                  onUploadNew={() => profileImageFlow.fileInputRef.current?.click()}
                  onEditCurrent={() => void profileImageFlow.handleEditCurrentImage()}
                />
                <StudentProfileDetailsSection
                  details={details}
                  isEditing={profileForm.isEditing}
                  values={profileForm.values}
                  validationErrors={profileForm.validationErrors}
                  dirty={profileForm.dirty}
                  submitting={profileForm.submitting}
                  submitError={profileForm.submitError}
                  submitSuccess={profileForm.submitSuccess}
                  onStartEditing={profileForm.startEditing}
                  onCancelEditing={profileForm.cancelEditing}
                  onUpdateField={profileForm.updateField}
                  onSaveChanges={profileForm.saveChanges}
                />
              </>
            ) : null}

            {activeTab === "account" ? (
              <>
                <StudentConnectedIdentitySection identity={connectedIdentity} />
                <StudentContactSection
                  contact={contact}
                  isEditing={phoneForm.isEditing}
                  phoneNumber={phoneForm.phoneNumber}
                  validationError={phoneForm.validationError}
                  dirty={phoneForm.dirty}
                  submitting={phoneForm.submitting}
                  submitError={phoneForm.submitError}
                  submitSuccess={phoneForm.submitSuccess}
                  onStartEditing={phoneForm.startEditing}
                  onCancelEditing={phoneForm.cancelEditing}
                  onUpdatePhoneNumber={phoneForm.updatePhoneNumber}
                  onSaveChanges={phoneForm.saveChanges}
                />
                <StudentAccountActions
                  onLogout={handleLogout}
                  loggingOut={loggingOut}
                />
              </>
            ) : null}

            {activeTab === "preferences" ? (
              <StudentExamPreferencesSection
                availableExams={examPreferencesForm.availableExams}
                selectedExamIds={examPreferencesForm.selectedExamIds}
                isEditing={examPreferencesForm.isEditing}
                loading={examPreferencesForm.loading}
                validationError={examPreferencesForm.validationError}
                dirty={examPreferencesForm.dirty}
                submitting={examPreferencesForm.submitting}
                submitError={examPreferencesForm.submitError}
                submitSuccess={examPreferencesForm.submitSuccess}
                onStartEditing={examPreferencesForm.startEditing}
                onCancelEditing={examPreferencesForm.cancelEditing}
                onToggleExam={examPreferencesForm.toggleExam}
                onSaveChanges={examPreferencesForm.saveChanges}
              />
            ) : null}

            {activeTab === "billing" ? (
              <StudentAccountBillingLauncher
                availableCreditsBadgeViewModel={billingGatewayBadgeViewModel}
                availableCredits={
                  billingOverviewQuery.viewModel?.wallet.available_credits ?? null
                }
                isLoading={billingOverviewQuery.isLoading}
                errorMessage={
                  billingOverviewQuery.isError
                    ? billingOverviewQuery.error?.message ??
                      "Billing data could not be loaded right now."
                    : null
                }
                onOpenOverview={() => router.push("/student-billing/overview")}
                onOpenSubscriptions={() => router.push("/student-billing/plans")}
                onOpenWallet={() => router.push("/student-billing/wallet")}
                onOpenHistory={() => router.push("/student-billing/history")}
              />
            ) : null}

          </div>
        </div>
      </StudentAccountShell>

      <StudentAccountProfileImageEditor
        isPreviewModalOpen={profileImageFlow.isPreviewModalOpen}
        previewImageUrl={profileImageFlow.previewImageUrl}
        hasUnsavedCrop={profileImageFlow.imageDraft?.hasUnsavedCrop ?? false}
        uploading={profileImageFlow.uploadState.uploading}
        errorMessage={profileImageFlow.uploadState.errorMessage}
        onOpenCrop={profileImageFlow.openCropModal}
        onApply={profileImageFlow.handleApplyUpload}
        onCancel={profileImageFlow.closePreviewModal}
        isCropModalOpen={profileImageFlow.isCropModalOpen}
        cropImageSrc={profileImageFlow.imageDraft?.originalPreviewUrl ?? null}
        crop={profileImageFlow.crop}
        zoom={profileImageFlow.zoom}
        onCropChange={profileImageFlow.setCrop}
        onZoomChange={profileImageFlow.setZoom}
        onCropComplete={(_croppedArea: Area, croppedAreaPixels: Area) =>
          profileImageFlow.setCropPixels(croppedAreaPixels)
        }
        onSaveCrop={profileImageFlow.handleSaveCrop}
        onUnsaveCrop={profileImageFlow.handleUnsaveCrop}
      />
    </>
  );
}