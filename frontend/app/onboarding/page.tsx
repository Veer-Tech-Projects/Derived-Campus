"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { completeStudentOnboarding } from "@/features/student-auth/api/student-auth-api";
import { OnboardingExperienceShell } from "@/features/student-auth/components/onboarding-experience-shell";
import { OnboardingStepIdentityScreen } from "@/features/student-auth/components/onboarding-step-identity-screen";
import { OnboardingStepPhoneScreen } from "@/features/student-auth/components/onboarding-step-phone-screen";
import { OnboardingStepExamsScreen } from "@/features/student-auth/components/onboarding-step-exams-screen";
import { ProfileImageCropModal } from "@/features/student-auth/components/profile-image-crop-modal";
import { ProfileImagePreviewModal } from "@/features/student-auth/components/profile-image-preview-modal";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";
import { studentAuthUiConfig } from "@/features/student-auth/config/student-auth-ui-config";
import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import { useProfileImageFlow } from "@/features/student-auth/hooks/use-profile-image-flow";
import { useStudentOnboardingState } from "@/features/student-auth/hooks/use-student-onboarding-state";
import type {
  OnboardingFormState,
  OnboardingStep,
  OnboardingSubmitState,
} from "@/features/student-auth/onboarding/onboarding-types";
import { validateStudentPhoneForOnboarding } from "@/features/student-auth/api/student-auth-api";

const TOTAL_STEPS = 3;

function normalizeInitialDisplayName(
  displayName: string | null | undefined,
  firstName: string | null | undefined,
  lastName: string | null | undefined,
): string {
  if (displayName && displayName.trim()) {
    return displayName;
  }

  return [firstName ?? "", lastName ?? ""].join(" ").trim();
}

function buildInitials(
  firstName: string,
  lastName: string,
  displayName: string,
): string {
  const source = displayName.trim() || `${firstName} ${lastName}`.trim();

  if (!source) {
    return "DC";
  }

  const parts = source.split(/\s+/).filter(Boolean);

  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function resolveCountryCodeDisplay(
  value: string | null | undefined,
): string {
  const normalized = (value ?? "").trim();

  if (!normalized) {
    return "";
  }

  if (normalized.startsWith("+")) {
    return normalized;
  }

  if (/^\d+$/.test(normalized)) {
    return `+${normalized}`;
  }

  return normalized;
}

function normalizePhoneInputForUi(value: string): string {
  return value.replace(/\D/g, "").slice(0, 10);
}

function isPhoneRelatedBackendMessage(message: string): boolean {
  const normalized = message.toLowerCase();

  return (
    normalized.includes("phone") ||
    normalized.includes("invalid phone") ||
    normalized.includes("only indian") ||
    normalized.includes("not possible") ||
    normalized.includes("not valid")
  );
}

export default function StudentOnboardingPage() {
  const router = useRouter();
  const { status, accessToken, refreshSession } = useStudentAuth();
  const {
    onboardingRequired,
    onboardingState,
    loading,
    errorMessage,
    reload,
  } = useStudentOnboardingState();

  const [formState, setFormState] = useState<OnboardingFormState>({
    firstName: "",
    lastName: "",
    displayName: "",
    phoneNumber: "",
    selectedExamIds: [],
  });

  const [currentStep, setCurrentStep] = useState<OnboardingStep>(1);
  const [formInitialized, setFormInitialized] = useState(false);

  const [submitState, setSubmitState] = useState<OnboardingSubmitState>({
    submitting: false,
    errorMessage: null,
  });

  const providerEmail = onboardingState?.bootstrap.provider_email ?? "";
  const canonicalProfileImageUrl =
    onboardingState?.profile.profile_image_url ??
    onboardingState?.bootstrap.provider_avatar_url ??
    null;

  const canonicalIsUsingUploadedAvatar = Boolean(
    onboardingState?.profile.profile_image_storage_key,
  );

  const countryCodeDisplay = resolveCountryCodeDisplay(
    onboardingState?.profile.phone_country_code,
  );

  const imageFlow = useProfileImageFlow({
    accessToken,
    currentProfileImageUrl: canonicalProfileImageUrl,
    canEditUploadedAvatar: canonicalIsUsingUploadedAvatar,
    refreshSession,
    reloadOnboardingState: reload,
  });

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(studentAuthRouteConfig.loginPath);
      return;
    }

    if (status === "authenticated_completed") {
      router.replace(studentAuthRouteConfig.postLoginPath);
    }
  }, [router, status]);

  useEffect(() => {
    if (!onboardingState || formInitialized) {
      return;
    }

    const bootstrap = onboardingState.bootstrap;
    const profile = onboardingState.profile;

    setFormState({
      firstName: bootstrap.first_name ?? profile.first_name ?? "",
      lastName: bootstrap.last_name ?? profile.last_name ?? "",
      displayName: normalizeInitialDisplayName(
        bootstrap.display_name ?? profile.display_name,
        bootstrap.first_name ?? profile.first_name,
        bootstrap.last_name ?? profile.last_name,
      ),
      phoneNumber: profile.phone_number_e164 ?? "",
      selectedExamIds: [],
    });

    setFormInitialized(true);
  }, [formInitialized, onboardingState]);

  const availableExams = onboardingState?.available_exam_preferences ?? [];

  const canRenderForm =
    (status === "authenticated_pending_onboarding" || status === "refreshing") &&
    onboardingRequired &&
    onboardingState &&
    formInitialized;

  const initials = useMemo(
    () =>
      buildInitials(
        formState.firstName,
        formState.lastName,
        formState.displayName,
      ),
    [formState.displayName, formState.firstName, formState.lastName],
  );

  const stepMeta = useMemo(() => {
    if (currentStep === 1) {
      return {
        title: "Confirm your identity",
        subtitle:
          "Review your personal details and profile image before continuing.",
        illustrationSrc: "/illustrations/student-auth/identity-illustration.svg",
        illustrationAlt: "Student profile setup illustration",
      };
    }

    if (currentStep === 2) {
      return {
        title: "Stay reachable",
        subtitle:
          "Add your phone number so your account remains secure and accessible.",
        illustrationSrc: "/illustrations/student-auth/phone-illustration.svg",
        illustrationAlt: "Phone and communication illustration",
      };
    }

    return {
      title: "Set your preferences",
      subtitle:
        "Choose the exams you care about so your experience is personalized from the start.",
      illustrationSrc:
        "/illustrations/student-auth/exam-preferences-illustration.svg",
      illustrationAlt: "Exam preferences illustration",
    };
  }, [currentStep]);

  function updateField<K extends keyof OnboardingFormState>(
    key: K,
    value: OnboardingFormState[K],
  ) {
    setFormState((prev) => ({
      ...prev,
      [key]: value,
    }));
  }

  function toggleExamSelection(examId: string) {
    setFormState((prev) => {
      const isSelected = prev.selectedExamIds.includes(examId);

      return {
        ...prev,
        selectedExamIds: isSelected
          ? prev.selectedExamIds.filter((id) => id !== examId)
          : [...prev.selectedExamIds, examId],
      };
    });
  }

  function validateStepOne(): string | null {
    if (!formState.firstName.trim()) {
      return "First name is required before you continue.";
    }

    if (!formState.lastName.trim()) {
      return "Last name is required before you continue.";
    }

    return null;
  }

  function validateStepTwo(): string | null {
    const normalizedPhone = normalizePhoneInputForUi(formState.phoneNumber);

    if (!normalizedPhone) {
      return "Phone number is required before you continue.";
    }

    if (normalizedPhone.length !== 10) {
      return "Please enter a valid 10-digit Indian mobile number.";
    }

    return null;
  }

  function validateStepThree(): string | null {
    if (formState.selectedExamIds.length === 0) {
      return "Please select at least one exam before completing onboarding.";
    }

    return null;
  }

  async function goToNextStep() {
    if (currentStep === 1) {
      const error = validateStepOne();

      if (error) {
        setSubmitState({ submitting: false, errorMessage: error });
        return;
      }

      setSubmitState({ submitting: false, errorMessage: null });
      setCurrentStep(2);
      return;
    }

    if (currentStep === 2) {
      const error = validateStepTwo();

      if (error) {
        setSubmitState({ submitting: false, errorMessage: error });
        return;
      }

      if (!accessToken) {
        setSubmitState({
          submitting: false,
          errorMessage: "No student access token is available.",
        });
        return;
      }

      setSubmitState({
        submitting: true,
        errorMessage: null,
      });

      try {
        await validateStudentPhoneForOnboarding(accessToken, {
          phone_number: normalizePhoneInputForUi(formState.phoneNumber),
        });

        setFormState((prev) => ({
          ...prev,
          phoneNumber: normalizePhoneInputForUi(prev.phoneNumber),
        }));

        setSubmitState({
          submitting: false,
          errorMessage: null,
        });

        setCurrentStep(3);
      } catch (error) {
        setSubmitState({
          submitting: false,
          errorMessage:
            error instanceof Error
              ? error.message
              : "Phone number validation failed.",
        });
      }
    }
  }

  function goBack() {
    setSubmitState({ submitting: false, errorMessage: null });

    if (currentStep === 3) {
      setCurrentStep(2);
      return;
    }

    if (currentStep === 2) {
      setCurrentStep(1);
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const error = validateStepThree();

    if (error) {
      setSubmitState({
        submitting: false,
        errorMessage: error,
      });
      return;
    }

    if (!accessToken) {
      setSubmitState({
        submitting: false,
        errorMessage: "No student access token is available.",
      });
      return;
    }

    setSubmitState({
      submitting: true,
      errorMessage: null,
    });

    try {
      const response = await completeStudentOnboarding(accessToken, {
        first_name: formState.firstName.trim(),
        last_name: formState.lastName.trim(),
        display_name: formState.displayName.trim() || null,
        phone_number: formState.phoneNumber.trim(),
        exam_preference_catalog_ids: formState.selectedExamIds,
        use_provider_avatar: true,
      });

      if (response.onboarding_status === "COMPLETED") {
        await refreshSession();
        router.replace(studentAuthRouteConfig.postLoginPath);
        return;
      }

      setSubmitState({
        submitting: false,
        errorMessage: "Onboarding did not complete successfully.",
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to complete onboarding.";

      if (isPhoneRelatedBackendMessage(message)) {
        setCurrentStep(2);
        setSubmitState({
          submitting: false,
          errorMessage: message,
        });
        return;
      }

      setSubmitState({
        submitting: false,
        errorMessage: message,
      });
    }
  }

  if (
    status === "unknown" ||
    ((status === "refreshing" || loading) && !onboardingState)
  ) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
        <div className="w-full max-w-2xl rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-8">
          <div className="space-y-4">
            <div className="h-6 w-48 animate-pulse rounded-md bg-muted" />
            <div className="h-4 w-full animate-pulse rounded-md bg-muted" />
            <div className="h-56 animate-pulse rounded-3xl bg-muted" />
            <div className="h-48 animate-pulse rounded-3xl bg-muted" />
          </div>
        </div>
      </div>
    );
  }

  if (status === "unauthenticated" || status === "authenticated_completed") {
    return null;
  }

  if (!canRenderForm) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
        <div className="w-full max-w-xl rounded-3xl border border-border bg-card p-6 text-sm shadow-sm sm:p-8">
          <div className="space-y-3">
            <h1 className="text-lg font-semibold">Unable to load onboarding</h1>
            <p className="text-muted-foreground">
              {errorMessage ?? "The onboarding state is not available right now."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <OnboardingExperienceShell
        currentStep={currentStep}
        totalSteps={TOTAL_STEPS}
        title={stepMeta.title}
        subtitle={stepMeta.subtitle}
        illustrationSrc={stepMeta.illustrationSrc}
        illustrationAlt={stepMeta.illustrationAlt}
        canGoBack={currentStep > 1}
        onBack={goBack}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {submitState.errorMessage && currentStep !== 2 ? (
            <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {submitState.errorMessage}
            </div>
          ) : null}

          {currentStep === 1 ? (
            <OnboardingStepIdentityScreen
              formState={formState}
              providerEmail={providerEmail || null}
              initials={initials}
              profileImageUrl={imageFlow.effectiveProfileImageUrl}
              providerLabel={onboardingState.bootstrap.provider}
              isUsingUploadedAvatar={imageFlow.effectiveCanEditUploadedAvatar}
              disabled={imageFlow.uploadState.uploading || submitState.submitting}
              errorMessage={imageFlow.uploadState.errorMessage}
              fileInputRef={imageFlow.fileInputRef}
              accept={studentAuthUiConfig.profileImageAllowedMimeTypes.join(",")}
              onFileChange={imageFlow.handleImageFileSelection}
              onUploadNew={() => imageFlow.fileInputRef.current?.click()}
              onEdit={() => void imageFlow.handleEditCurrentImage()}
              onChange={updateField}
              onContinue={goToNextStep}
            />
          ) : null}

          {currentStep === 2 ? (
            <OnboardingStepPhoneScreen
              phoneNumber={formState.phoneNumber}
              countryCodeDisplay={countryCodeDisplay}
              disabled={submitState.submitting}
              errorMessage={currentStep === 2 ? submitState.errorMessage : null}
              onChange={(value) =>
                updateField("phoneNumber", normalizePhoneInputForUi(value))
              }
              onBack={goBack}
              onContinue={() => void goToNextStep()}
            />
          ) : null}

          {currentStep === 3 ? (
            <OnboardingStepExamsScreen
              exams={availableExams}
              selectedExamIds={formState.selectedExamIds}
              submitting={submitState.submitting}
              onToggle={toggleExamSelection}
              onBack={goBack}
            />
          ) : null}
        </form>
      </OnboardingExperienceShell>

      <ProfileImagePreviewModal
        open={imageFlow.isPreviewModalOpen}
        previewImageUrl={imageFlow.previewImageUrl}
        hasUnsavedCrop={imageFlow.imageDraft?.hasUnsavedCrop ?? false}
        uploading={imageFlow.uploadState.uploading}
        errorMessage={imageFlow.uploadState.errorMessage}
        onCrop={imageFlow.openCropModal}
        onApply={() => void imageFlow.handleApplyUpload()}
        onCancel={imageFlow.closePreviewModal}
      />

      <ProfileImageCropModal
        open={imageFlow.isCropModalOpen}
        imageSrc={imageFlow.imageDraft?.originalPreviewUrl ?? null}
        crop={imageFlow.crop}
        zoom={imageFlow.zoom}
        onCropChange={imageFlow.setCrop}
        onZoomChange={imageFlow.setZoom}
        onCropComplete={(_, croppedAreaPixels) => {
          imageFlow.setCropPixels(croppedAreaPixels);
        }}
        onSaveCrop={() => void imageFlow.handleSaveCrop()}
        onUnsave={imageFlow.handleUnsaveCrop}
      />
    </>
  );
}