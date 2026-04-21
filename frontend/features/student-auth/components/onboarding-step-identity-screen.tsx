"use client";

import type { OnboardingFormState } from "../onboarding/onboarding-types";
import { OnboardingAvatarCard } from "./onboarding-avatar-card";

type OnboardingStepIdentityScreenProps = {
  formState: OnboardingFormState;
  providerEmail: string | null;
  initials: string;
  profileImageUrl: string | null;
  providerLabel: string;
  isUsingUploadedAvatar: boolean;
  disabled: boolean;
  errorMessage: string | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  accept: string;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onUploadNew: () => void;
  onEdit: () => void;
  onChange: <K extends keyof OnboardingFormState>(
    key: K,
    value: OnboardingFormState[K],
  ) => void;
  onContinue: () => void;
};

export function OnboardingStepIdentityScreen({
  formState,
  providerEmail,
  initials,
  profileImageUrl,
  providerLabel,
  isUsingUploadedAvatar,
  disabled,
  errorMessage,
  fileInputRef,
  accept,
  onFileChange,
  onUploadNew,
  onEdit,
  onChange,
  onContinue,
}: OnboardingStepIdentityScreenProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">
          Confirm your identity
        </h2>
        <p className="text-sm leading-6 text-muted-foreground">
          Review your profile details before continuing to the next step.
        </p>
      </div>

      <div className="onb-panel-muted rounded-[1.75rem] border border-border/60 p-5 sm:p-6">
        <OnboardingAvatarCard
          profileImageUrl={profileImageUrl}
          initials={initials}
          providerLabel={providerLabel}
          providerEmail={providerEmail}
          isUsingUploadedAvatar={isUsingUploadedAvatar}
          disabled={disabled}
          errorMessage={errorMessage}
          fileInputRef={fileInputRef}
          accept={accept}
          onFileChange={onFileChange}
          onUploadNew={onUploadNew}
          onEdit={onEdit}
        />
      </div>

      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm font-semibold text-foreground">
              First name
            </span>
            <input
              value={formState.firstName}
              onChange={(event) => onChange("firstName", event.target.value)}
              className="h-14 w-full rounded-2xl border border-border/70 bg-background px-4 text-sm font-medium text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
              placeholder="Enter first name"
              autoComplete="given-name"
              required
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-semibold text-foreground">
              Last name
            </span>
            <input
              value={formState.lastName}
              onChange={(event) => onChange("lastName", event.target.value)}
              className="h-14 w-full rounded-2xl border border-border/70 bg-background px-4 text-sm font-medium text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
              placeholder="Enter last name"
              autoComplete="family-name"
              required
            />
          </label>
        </div>

        <label className="space-y-2">
          <span className="text-sm font-semibold text-foreground">
            Display name
          </span>
          <input
            value={formState.displayName}
            onChange={(event) => onChange("displayName", event.target.value)}
            className="h-14 w-full rounded-2xl border border-border/70 bg-background px-4 text-sm font-medium text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
            placeholder="Enter display name"
            autoComplete="nickname"
          />
        </label>
      </div>

      {providerEmail ? (
        <div className="pt-0">
          <div className="rounded-[1.5rem] border border-border/80 bg-secondary/35 p-4 sm:p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  Connected email
                </p>
                <p className="mt-2 break-all text-sm leading-6 text-muted-foreground">
                  {providerEmail}
                </p>
              </div>

              <span className="shrink-0 rounded-full border border-border/70 bg-background px-3 py-1 text-xs font-semibold text-muted-foreground">
                Read only
              </span>
            </div>
          </div>
        </div>
      ) : null}

      <div className="pt-2">
        <button
          type="button"
          onClick={onContinue}
          disabled={disabled}
          className="flex h-13 w-full items-center justify-center rounded-2xl bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-60"
        >
          Continue
        </button>
      </div>
    </div>
  );
}