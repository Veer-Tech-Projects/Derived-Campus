"use client";

import { Crop, ImagePlus } from "lucide-react";

type Props = {
  open: boolean;
  previewImageUrl: string | null;
  hasUnsavedCrop: boolean;
  uploading: boolean;
  errorMessage: string | null;
  onCrop: () => void;
  onApply: () => void;
  onCancel: () => void;
};

export function ProfileImagePreviewModal({
  open,
  previewImageUrl,
  hasUnsavedCrop,
  uploading,
  errorMessage,
  onCrop,
  onApply,
  onCancel,
}: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
      <div className="flex min-h-screen items-center justify-center p-3 sm:p-4 lg:p-6">
        <div className="flex max-h-[calc(100vh-1.5rem)] w-full max-w-5xl flex-col overflow-hidden rounded-[2rem] border border-border bg-card shadow-2xl sm:max-h-[calc(100vh-2rem)] lg:max-h-[calc(100vh-3rem)]">
          <div className="shrink-0 border-b border-border px-5 py-4 sm:px-6">
            <h3 className="text-lg font-semibold text-foreground sm:text-xl">
              Profile image preview
            </h3>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Review your selected image. Crop is optional. Apply uploads only the
              final preview.
            </p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6 sm:py-6">
            <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">Preview</p>

                  <button
                    type="button"
                    onClick={onCrop}
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground shadow-sm transition hover:bg-accent hover:text-accent-foreground"
                    aria-label="Open crop tool"
                    title="Open crop tool"
                  >
                    <Crop className="h-4 w-4" />
                    Crop image
                  </button>
                </div>

                <div className="overflow-hidden rounded-[1.75rem] border border-border bg-background shadow-sm">
                  {previewImageUrl ? (
                    <img
                      src={previewImageUrl}
                      alt="Profile preview"
                      className="max-h-[52vh] w-full object-contain sm:max-h-[56vh] lg:max-h-[58vh]"
                    />
                  ) : (
                    <div className="flex min-h-[260px] items-center justify-center bg-muted text-sm text-muted-foreground">
                      No preview available
                    </div>
                  )}
                </div>

                <p className="text-xs leading-6 text-muted-foreground">
                  {hasUnsavedCrop
                    ? "A saved crop is currently selected and will be used if you apply."
                    : "The current preview will be used if you apply now."}
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-[1.5rem] border border-border/70 bg-secondary/30 p-4 sm:p-5">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-background text-foreground shadow-sm">
                      <ImagePlus className="h-4 w-4" />
                    </div>

                    <div>
                      <p className="text-sm font-semibold text-foreground">
                        How this works
                      </p>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Cancel closes this preview without uploading anything.
                        Apply uploads only the final image shown here.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  <button
                    type="button"
                    onClick={onApply}
                    disabled={uploading}
                    className="flex h-12 w-full items-center justify-center rounded-2xl bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-60"
                  >
                    {uploading ? "Applying..." : "Apply"}
                  </button>

                  <button
                    type="button"
                    onClick={onCancel}
                    disabled={uploading}
                    className="flex h-12 w-full items-center justify-center rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
                  >
                    Cancel
                  </button>
                </div>

                {errorMessage ? (
                  <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                    {errorMessage}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}