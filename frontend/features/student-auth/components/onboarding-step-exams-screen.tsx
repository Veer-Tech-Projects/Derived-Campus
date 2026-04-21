"use client";

type ExamOption = {
  id: string;
  visible_label: string;
  description: string | null;
};

type OnboardingStepExamsScreenProps = {
  exams: ExamOption[];
  selectedExamIds: string[];
  submitting: boolean;
  onToggle: (examId: string) => void;
  onBack: () => void;
};

export function OnboardingStepExamsScreen({
  exams,
  selectedExamIds,
  submitting,
  onToggle,
  onBack,
}: OnboardingStepExamsScreenProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">
          Choose your exam preferences
        </h2>
        <p className="text-sm leading-6 text-muted-foreground">
          These choices help us personalize your discovery experience and keep
          the platform relevant to your goals.
        </p>
      </div>

      <div className="flex items-center justify-between gap-3 rounded-2xl border border-border/60 bg-background/80 px-4 py-3">
        <p className="text-sm font-semibold text-foreground">
          Available exams
        </p>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          {selectedExamIds.length} selected
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {exams.map((exam) => {
          const isSelected = selectedExamIds.includes(exam.id);

          return (
            <button
              key={exam.id}
              type="button"
              onClick={() => onToggle(exam.id)}
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

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={submitting}
          className="flex h-12 items-center justify-center rounded-2xl border border-border/70 bg-background px-5 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
        >
          Back
        </button>

        <button
          type="submit"
          disabled={submitting}
          className="flex h-12 min-w-[190px] items-center justify-center rounded-2xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-60"
        >
          {submitting ? "Finalizing..." : "Complete onboarding"}
        </button>
      </div>
    </div>
  );
}