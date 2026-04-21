"use client";

import { Pencil, Upload } from "lucide-react";

type OnboardingAvatarCardProps = {
  profileImageUrl: string | null;
  initials: string;
  providerLabel: string;
  providerEmail: string | null;
  isUsingUploadedAvatar: boolean;
  disabled?: boolean;
  errorMessage?: string | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  accept: string;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onUploadNew: () => void;
  onEdit: () => void;
};

export function OnboardingAvatarCard({
  profileImageUrl,
  initials,
  providerLabel,
  providerEmail,
  isUsingUploadedAvatar,
  disabled = false,
  errorMessage,
  fileInputRef,
  accept,
  onFileChange,
  onUploadNew,
  onEdit,
}: OnboardingAvatarCardProps) {
  return (
    <div className="space-y-5">
      <div className="flex flex-col items-center justify-center">
        <div className="relative">
          <div className="flex h-28 w-28 items-center justify-center overflow-hidden rounded-full border border-border/70 bg-background shadow-[0_10px_30px_rgba(0,0,0,0.08)] sm:h-32 sm:w-32">
            {profileImageUrl ? (
              <img
                src={profileImageUrl}
                alt="Student avatar"
                className="h-full w-full object-cover"
                loading="lazy"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-muted text-2xl font-semibold text-muted-foreground">
                {initials}
              </div>
            )}
          </div>

          {isUsingUploadedAvatar ? (
            <button
              type="button"
              onClick={onEdit}
              disabled={disabled}
              aria-label="Edit profile image"
              title="Edit profile image"
              className="absolute -bottom-1 -right-1 inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground shadow-[0_8px_24px_rgba(0,0,0,0.12)] transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
            >
              <Pencil className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        <div className="mt-4 text-center">
          <p className="text-sm font-semibold text-foreground">
            {isUsingUploadedAvatar ? "Profile photo ready" : `Connected with ${providerLabel}`}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {isUsingUploadedAvatar
              ? "Upload a new image anytime if you want to replace the current one."
              : "You can keep this image or upload a more personal profile photo."}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={onUploadNew}
          disabled={disabled}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
        >
          <Upload className="h-4 w-4" />
          {isUsingUploadedAvatar ? "Replace photo" : "Upload photo"}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={onFileChange}
        />
      </div>

      {errorMessage ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {errorMessage}
        </div>
      ) : null}
    </div>
  );
}