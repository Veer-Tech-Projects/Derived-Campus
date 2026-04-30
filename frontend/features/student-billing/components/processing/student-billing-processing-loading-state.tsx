"use client";

export function StudentBillingProcessingLoadingState() {
  return (
    <div className="rounded-[1.5rem] border border-border bg-secondary/40 p-6">
      <div className="flex flex-col items-center text-center">
        <div className="mb-5 h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <h2 className="text-lg font-semibold text-foreground">
          Verifying your payment
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
          We are securely checking your billing order with the backend before
          credits are granted to your wallet.
        </p>
      </div>
    </div>
  );
}