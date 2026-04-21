"use client";

import { PencilLine, Save, X } from "lucide-react";

type StudentProfileDetailsViewModel = {
  firstName: string;
  lastName: string;
  displayName: string | null;
};

type StudentProfileDetailsSectionProps = {
  details: StudentProfileDetailsViewModel;
  isEditing: boolean;
  values: {
    firstName: string;
    lastName: string;
    displayName: string;
  };
  validationErrors: {
    firstName: string | null;
    lastName: string | null;
    displayName: string | null;
  };
  dirty: boolean;
  submitting: boolean;
  submitError: string | null;
  submitSuccess: string | null;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onUpdateField: (
    key: "firstName" | "lastName" | "displayName",
    value: string,
  ) => void;
  onSaveChanges: () => void | Promise<void>;
};

type FieldCardProps = {
  label: string;
  value: string;
};

function FieldCard({ label, value }: FieldCardProps) {
  return (
    <div className="rounded-[1.4rem] border border-border/60 bg-background/70 px-4 py-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-base font-semibold text-foreground">{value}</p>
    </div>
  );
}

type EditableFieldProps = {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  maxLength: number;
  errorMessage: string | null;
  onChange: (value: string) => void;
};

function EditableField({
  id,
  label,
  value,
  placeholder,
  maxLength,
  errorMessage,
  onChange,
}: EditableFieldProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="text-sm font-semibold text-foreground"
      >
        {label}
      </label>

      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        className={`h-12 w-full rounded-2xl border bg-background px-4 text-sm text-foreground outline-none transition placeholder:text-muted-foreground/70 focus:ring-2 ${
          errorMessage
            ? "border-destructive/50 focus:border-destructive focus:ring-destructive/20"
            : "border-border/70 focus:border-primary focus:ring-primary/20"
        }`}
      />

      <div className="flex items-center justify-between gap-3">
        <div className="min-h-[1.25rem] text-xs text-destructive">
          {errorMessage ?? ""}
        </div>
        <div className="text-xs text-muted-foreground">
          {value.length}/{maxLength}
        </div>
      </div>
    </div>
  );
}

export function StudentProfileDetailsSection({
  details,
  isEditing,
  values,
  validationErrors,
  dirty,
  submitting,
  submitError,
  submitSuccess,
  onStartEditing,
  onCancelEditing,
  onUpdateField,
  onSaveChanges,
}: StudentProfileDetailsSectionProps) {
  return (
    <section className="rounded-[2rem] bg-card p-6 shadow-[0_8px_30px_rgba(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.1)]">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-foreground">
            Profile details
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Your editable student identity information.
          </p>
        </div>

        {!isEditing ? (
          <button
            type="button"
            onClick={onStartEditing}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground"
          >
            <PencilLine className="h-4 w-4" />
            Edit details
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
        <div className="grid gap-4 md:grid-cols-2">
          <FieldCard label="First name" value={details.firstName} />
          <FieldCard label="Last name" value={details.lastName} />
          <div className="md:col-span-2">
            <FieldCard
              label="Display name"
              value={details.displayName ?? "Not set"}
            />
          </div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <EditableField
              id="student-account-first-name"
              label="First name"
              value={values.firstName}
              placeholder="Enter first name"
              maxLength={100}
              errorMessage={validationErrors.firstName}
              onChange={(value) => onUpdateField("firstName", value)}
            />

            <EditableField
              id="student-account-last-name"
              label="Last name"
              value={values.lastName}
              placeholder="Enter last name"
              maxLength={100}
              errorMessage={validationErrors.lastName}
              onChange={(value) => onUpdateField("lastName", value)}
            />

            <div className="md:col-span-2">
              <EditableField
                id="student-account-display-name"
                label="Display name"
                value={values.displayName}
                placeholder="Enter display name"
                maxLength={200}
                errorMessage={validationErrors.displayName}
                onChange={(value) => onUpdateField("displayName", value)}
              />
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