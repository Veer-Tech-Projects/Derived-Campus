"use client";

import { PencilLine, Phone, Save, X } from "lucide-react";
import type { StudentContactViewModel } from "../types/student-account-view-models";

type StudentContactSectionProps = {
  contact: StudentContactViewModel;
  isEditing: boolean;
  phoneNumber: string;
  validationError: string | null;
  dirty: boolean;
  submitting: boolean;
  submitError: string | null;
  submitSuccess: string | null;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onUpdatePhoneNumber: (value: string) => void;
  onSaveChanges: () => void | Promise<void>;
};

export function StudentContactSection({
  contact,
  isEditing,
  phoneNumber,
  validationError,
  dirty,
  submitting,
  submitError,
  submitSuccess,
  onStartEditing,
  onCancelEditing,
  onUpdatePhoneNumber,
  onSaveChanges,
}: StudentContactSectionProps) {
  return (
    <section className="rounded-[2rem] bg-card p-6 shadow-[0_8px_30px_rgba(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.1)]">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[1.1rem] bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400">
            <Phone className="h-6 w-6" />
          </div>

          <div>
            <h3 className="text-lg font-bold tracking-tight text-foreground">
              Phone number
            </h3>
            <p className="text-sm text-muted-foreground">
              Used for alerts and recovery.
            </p>
          </div>
        </div>

        {!isEditing ? (
          <button
            type="button"
            onClick={onStartEditing}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground"
          >
            <PencilLine className="h-4 w-4" />
            Edit phone
          </button>
        ) : null}
      </div>

      {submitError ? (
        <div className="mb-4 rounded-[1.25rem] border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {submitError}
        </div>
      ) : null}

      {submitSuccess ? (
        <div className="mb-4 rounded-[1.25rem] border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-400">
          {submitSuccess}
        </div>
      ) : null}

      {!isEditing ? (
        <div className="rounded-[1.5rem] bg-secondary/50 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Current phone number
          </p>
          <p className="mt-2 text-lg font-bold tracking-wide text-foreground">
            {contact.phoneNumber || "Not provided"}
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-[1.5rem] bg-secondary/50 p-5">
            <label
              htmlFor="student-account-phone-number"
              className="text-sm font-semibold text-foreground"
            >
              Mobile number
            </label>

            <div className="mt-3 flex items-center overflow-hidden rounded-2xl border border-border/70 bg-background focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
              <div className="flex h-12 items-center border-r border-border/60 px-4 text-sm font-semibold text-muted-foreground">
                +91
              </div>

              <input
                id="student-account-phone-number"
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                value={phoneNumber}
                placeholder="Enter 10-digit mobile number"
                maxLength={10}
                onChange={(event) => onUpdatePhoneNumber(event.target.value)}
                className="h-12 w-full bg-transparent px-4 text-sm font-medium text-foreground outline-none placeholder:text-muted-foreground/70"
              />
            </div>

            <div className="mt-2 flex items-center justify-between gap-3">
              <div className="min-h-[1.25rem] text-xs text-destructive">
                {validationError ?? ""}
              </div>
              <div className="text-xs text-muted-foreground">
                {phoneNumber.length}/10
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onCancelEditing}
              disabled={submitting}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
            >
              <X className="h-4 w-4" />
              Cancel
            </button>

            <button
              type="button"
              onClick={() => void onSaveChanges()}
              disabled={submitting || !dirty}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-60"
            >
              <Save className="h-4 w-4" />
              {submitting ? "Saving..." : "Save changes"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}