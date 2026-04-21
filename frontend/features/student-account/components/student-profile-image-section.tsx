"use client";

import { Camera, Image as ImageIcon, Pencil, Upload } from "lucide-react";

type StudentProfileImageSectionProps = {
  profileImageUrl: string | null;
  canEditUploadedAvatar: boolean;
  disabled?: boolean;
  errorMessage?: string | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  accept: string;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onUploadNew: () => void;
  onEditCurrent: () => void;
};

export function StudentProfileImageSection({
  profileImageUrl,
  canEditUploadedAvatar,
  disabled = false,
  errorMessage = null,
  fileInputRef,
  accept,
  onFileChange,
  onUploadNew,
  onEditCurrent,
}: StudentProfileImageSectionProps) {
  return (
    <section className="rounded-[2rem] bg-card p-6 shadow-[0_8px_30px_rgba(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.1)]">
      <div className="mb-6 flex items-center gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[1.1rem] bg-pink-500/10 text-pink-600 dark:bg-pink-500/20 dark:text-pink-400">
          <Camera className="h-6 w-6" />
        </div>

        <div>
          <h3 className="text-lg font-bold tracking-tight text-foreground">
            Profile image
          </h3>
          <p className="text-sm text-muted-foreground">
            Your account photo.
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center gap-5 sm:flex-row">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full border-4 border-background bg-secondary shadow-md">
          {profileImageUrl ? (
            <img
              src={profileImageUrl}
              alt="Student profile"
              className="h-full w-full object-cover"
              loading="lazy"
              referrerPolicy="no-referrer"
            />
          ) : (
            <ImageIcon className="h-8 w-8 text-muted-foreground" />
          )}
        </div>

        <div className="flex-1 space-y-4">
          <div className="rounded-[1.5rem] bg-secondary/50 p-4">
            <p className="text-sm font-bold text-foreground">
              {profileImageUrl ? "Configured successfully" : "No custom photo yet"}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {profileImageUrl
                ? "You can replace or edit the current uploaded image anytime."
                : "Upload a profile image to personalize your account experience."}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={onUploadNew}
              disabled={disabled}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-60"
            >
              <Upload className="h-4 w-4" />
              {canEditUploadedAvatar ? "Replace photo" : "Upload photo"}
            </button>

            {canEditUploadedAvatar ? (
              <button
                type="button"
                onClick={onEditCurrent}
                disabled={disabled}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
              >
                <Pencil className="h-4 w-4" />
                Edit current
              </button>
            ) : null}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept={accept}
            className="hidden"
            onChange={onFileChange}
          />

          {errorMessage ? (
            <div className="rounded-[1.25rem] border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {errorMessage}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}