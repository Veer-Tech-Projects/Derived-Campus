"use client";

type OnboardingStepPhoneScreenProps = {
  phoneNumber: string;
  countryCodeDisplay: string;
  disabled: boolean;
  errorMessage?: string | null;
  onChange: (value: string) => void;
  onBack: () => void;
  onContinue: () => void;
};

export function OnboardingStepPhoneScreen({
  phoneNumber,
  countryCodeDisplay,
  disabled,
  errorMessage = null,
  onChange,
  onBack,
  onContinue,
}: OnboardingStepPhoneScreenProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">
          Add your phone number
        </h2>
        <p className="text-sm leading-6 text-muted-foreground">
          We use this for important account communication, session recovery, and
          student-facing updates.
        </p>
      </div>

      <div className="onb-panel-muted rounded-[1.5rem] border border-border/60 p-4 sm:p-5">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-foreground">
            Phone number
          </span>

          <div className="flex h-14 w-full overflow-hidden rounded-2xl border border-border/70 bg-background">
            <div className="flex min-w-[84px] items-center justify-center border-r border-border/70 bg-secondary px-4 text-sm font-semibold text-secondary-foreground">
              {countryCodeDisplay || "—"}
            </div>

            <input
              value={phoneNumber}
              onChange={(event) => onChange(event.target.value)}
              className="h-full w-full bg-transparent px-4 text-sm font-medium text-foreground outline-none placeholder:text-muted-foreground/60"
              placeholder="Enter your 10-digit mobile number"
              inputMode="numeric"
              autoComplete="tel-national"
              maxLength={10}
              pattern="[0-9]*"
              required
            />
          </div>
        </label>

        <div className="mt-4 rounded-2xl border border-border/60 bg-background/80 p-4">
          <p className="text-xs leading-6 text-muted-foreground">
            Keep this number active so you do not miss onboarding updates or
            important guidance-related communication.
          </p>
        </div>
      </div>

      {errorMessage ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {errorMessage}
        </div>
      ) : null}

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={disabled}
          className="flex h-12 items-center justify-center rounded-2xl border border-border/70 bg-background px-5 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
        >
          Back
        </button>

        <button
          type="button"
          onClick={onContinue}
          disabled={disabled}
          className="flex h-12 min-w-[160px] items-center justify-center rounded-2xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-95 disabled:pointer-events-none disabled:opacity-60"
        >
          Continue
        </button>
      </div>
    </div>
  );
}