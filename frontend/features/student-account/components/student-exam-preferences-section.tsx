"use client";

import { PencilLine, Save, X } from "lucide-react";
import type { StudentExamPreferenceCatalogItemDTO } from "@/features/student-auth/types/student-auth-contracts";

type StudentExamPreferencesSectionProps = {
  availableExams: StudentExamPreferenceCatalogItemDTO[];
  selectedExamIds: string[];
  isEditing: boolean;
  loading: boolean;
  validationError: string | null;
  dirty: boolean;
  submitting: boolean;
  submitError: string | null;
  submitSuccess: string | null;
  onStartEditing: () => void;
  onCancelEditing: () => void;
  onToggleExam: (examId: string) => void;
  onSaveChanges: () => void | Promise<void>;
};

export function StudentExamPreferencesSection({
  availableExams,
  selectedExamIds,
  isEditing,
  loading,
  validationError,
  dirty,
  submitting,
  submitError,
  submitSuccess,
  onStartEditing,
  onCancelEditing,
  onToggleExam,
  onSaveChanges,
}: StudentExamPreferencesSectionProps) {
  const selectedExams = availableExams.filter((exam) =>
    selectedExamIds.includes(exam.id),
  );

  return (
    <section className="rounded-[2rem] bg-card p-6 shadow-[0_8px_30px_rgba(0,0,0,0.04)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.1)]">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-foreground">
            Exam preferences
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage the exams that personalize your student experience.
          </p>
        </div>

        {!isEditing && !loading ? (
          <button
            type="button"
            onClick={onStartEditing}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-border/70 bg-background px-4 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground"
          >
            <PencilLine className="h-4 w-4" />
            Edit preferences
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

      {loading ? (
        <div className="space-y-4">
          <div className="h-14 animate-pulse rounded-2xl bg-secondary/50" />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="h-28 animate-pulse rounded-[1.5rem] bg-secondary/40" />
            <div className="h-28 animate-pulse rounded-[1.5rem] bg-secondary/40" />
            <div className="h-28 animate-pulse rounded-[1.5rem] bg-secondary/40" />
            <div className="h-28 animate-pulse rounded-[1.5rem] bg-secondary/40" />
          </div>
        </div>
      ) : !isEditing ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 rounded-2xl border border-border/60 bg-background/80 px-4 py-3">
            <p className="text-sm font-semibold text-foreground">
              Selected exam preferences
            </p>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              {selectedExamIds.length} selected
            </span>
          </div>

          {selectedExams.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {selectedExams.map((exam) => (
                <div
                  key={exam.id}
                  className="rounded-[1.5rem] border border-primary/20 bg-primary/6 p-4 shadow-sm"
                >
                  <p className="text-sm font-semibold text-primary">
                    {exam.visible_label}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {exam.description ?? "Standard entrance examination."}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-[1.5rem] border border-dashed border-border/70 bg-background/60 p-6 text-sm text-muted-foreground">
              No exam preferences selected.
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-border/60 bg-background/80 px-4 py-3">
            <p className="text-sm font-semibold text-foreground">
              Available exams
            </p>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              {selectedExamIds.length} selected
            </span>
          </div>

          {validationError ? (
            <div className="mb-4 rounded-[1.25rem] border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {validationError}
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            {availableExams.map((exam) => {
              const isSelected = selectedExamIds.includes(exam.id);

              return (
                <button
                  key={exam.id}
                  type="button"
                  onClick={() => onToggleExam(exam.id)}
                  className={[
                    "group rounded-[1.5rem] border p-4 text-left transition",
                    isSelected
                      ? "border-primary bg-primary/6 shadow-sm"
                      : "border-border/70 bg-background hover:border-primary/40 hover:bg-secondary/40",
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p
                        className={[
                          "text-sm font-semibold",
                          isSelected ? "text-primary" : "text-foreground",
                        ].join(" ")}
                      >
                        {exam.visible_label}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-muted-foreground">
                        {exam.description ?? "Standard entrance examination."}
                      </p>
                    </div>

                    <div
                      className={[
                        "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold",
                        isSelected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border/70 bg-background text-transparent",
                      ].join(" ")}
                    >
                      ✓
                    </div>
                  </div>
                </button>
              );
            })}
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