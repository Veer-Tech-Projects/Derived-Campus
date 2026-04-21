"use client";

type StudentAccountActionsProps = {
  onLogout: () => void | Promise<void>;
  loggingOut?: boolean;
};

export function StudentAccountActions({
  onLogout,
  loggingOut = false,
}: StudentAccountActionsProps) {
  return (
    <section className="rounded-[1.75rem] border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold tracking-tight text-foreground">
          Account actions
        </h3>
        <p className="text-sm leading-6 text-muted-foreground">
          Use this section to securely end your current student session.
        </p>
      </div>

      <div className="mt-5">
        <button
          type="button"
          onClick={() => void onLogout()}
          disabled={loggingOut}
          className="inline-flex h-11 items-center justify-center rounded-2xl border border-border/70 bg-background px-5 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-60"
        >
          {loggingOut ? "Signing out..." : "Logout"}
        </button>
      </div>
    </section>
  );
}