"use client";

type TerminalVariant = "failed" | "cancelled" | "expired";

type StudentBillingProcessingTerminalStateProps = {
  variant: TerminalVariant;
  onGoBack: () => void;
};

function getVariantContent(variant: TerminalVariant): {
  title: string;
  description: string;
} {
  switch (variant) {
    case "failed":
      return {
        title: "Payment could not be confirmed",
        description:
          "We did not receive a successful backend-confirmed settlement for this order. You can return and start a fresh purchase safely.",
      };
    case "cancelled":
      return {
        title: "Checkout was closed",
        description:
          "No backend-confirmed payment was detected for this order. You can return and try again whenever you are ready.",
      };
    case "expired":
      return {
        title: "This billing order expired",
        description:
          "The order can no longer be completed. Please return and create a new purchase.",
      };
  }
}

export function StudentBillingProcessingTerminalState({
  variant,
  onGoBack,
}: StudentBillingProcessingTerminalStateProps) {
  const content = getVariantContent(variant);

  return (
    <div className="space-y-6">
      <div className="rounded-[1.5rem] border border-border bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-foreground">
          {content.title}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {content.description}
        </p>
      </div>

      <button
        type="button"
        onClick={onGoBack}
        className="inline-flex items-center justify-center rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
      >
        Return to account
      </button>
    </div>
  );
}