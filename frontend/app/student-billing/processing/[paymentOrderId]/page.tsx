"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";
import { useStudentBillingProcessingStatus } from "@/features/student-billing/hooks/use-student-billing-processing-status";
import { StudentBillingProcessingShell } from "@/features/student-billing/components/processing/student-billing-processing-shell";
import { StudentBillingProcessingLoadingState } from "@/features/student-billing/components/processing/student-billing-processing-loading-state";
import { StudentBillingProcessingPendingState } from "@/features/student-billing/components/processing/student-billing-processing-pending-state";
import { StudentBillingProcessingSuccessState } from "@/features/student-billing/components/processing/student-billing-processing-success-state";
import { StudentBillingProcessingManualReviewState } from "@/features/student-billing/components/processing/student-billing-processing-manual-review-state";
import { StudentBillingProcessingTerminalState } from "@/features/student-billing/components/processing/student-billing-processing-terminal-state";
import { formatCurrencyMinor } from "@/features/student-billing/utils/student-billing-formatters";

type StudentBillingProcessingPageProps = {
  params: Promise<{
    paymentOrderId: string;
  }>;
};

export default function StudentBillingProcessingPage({
  params,
}: StudentBillingProcessingPageProps) {
  const router = useRouter();
  const { status, accessToken } = useStudentAuth();
  const [paymentOrderId, setPaymentOrderId] = React.useState<string>("");

  useEffect(() => {
    let cancelled = false;

    void params.then((resolved) => {
      if (cancelled) {
        return;
      }

      setPaymentOrderId(resolved.paymentOrderId ?? "");
    });

    return () => {
      cancelled = true;
    };
  }, [params]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(studentAuthRouteConfig.loginPath);
      return;
    }

    if (status === "authenticated_pending_onboarding") {
      router.replace(studentAuthRouteConfig.onboardingPath);
    }
  }, [router, status]);

  const processing = useStudentBillingProcessingStatus({
    accessToken,
    paymentOrderId,
    redirectTo: "/student-billing/overview",
  });

  if (status === "unknown" || status === "refreshing" || !paymentOrderId) {
    return (
      <StudentBillingProcessingShell
        eyebrow="Billing verification"
        title="Preparing payment verification"
        description="Please wait while we load your billing verification page."
      >
        <StudentBillingProcessingLoadingState />
      </StudentBillingProcessingShell>
    );
  }

  const orderStatus = processing.orderStatus;
  const amountLabel =
    orderStatus
      ? formatCurrencyMinor(orderStatus.amount_minor, orderStatus.currency_code)
      : undefined;

  const handleGoBack = () => {
    router.replace("/student-account?tab=billing");
  };

  if (processing.pageState === "settled") {
    return (
      <StudentBillingProcessingShell
        eyebrow="Payment verified"
        title="Your credits are ready"
        description="Backend verification is complete and your billing wallet has been updated."
        orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
      >
        <StudentBillingProcessingSuccessState
          creditAmount={orderStatus?.credit_amount}
          amountLabel={amountLabel}
          countdownSeconds={processing.countdownSeconds}
          onGoNow={processing.redirectNow}
        />
      </StudentBillingProcessingShell>
    );
  }

  if (processing.pageState === "failed") {
    return (
      <StudentBillingProcessingShell
        eyebrow="Billing update"
        title="Payment could not be completed"
        description="We finished checking this order and it was not settled successfully."
        orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
      >
        <StudentBillingProcessingTerminalState
          variant="failed"
          onGoBack={handleGoBack}
        />
      </StudentBillingProcessingShell>
    );
  }

  if (processing.pageState === "cancelled") {
    return (
      <StudentBillingProcessingShell
        eyebrow="Billing update"
        title="Checkout was closed"
        description="No backend-confirmed payment was detected for this order."
        orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
      >
        <StudentBillingProcessingTerminalState
          variant="cancelled"
          onGoBack={handleGoBack}
        />
      </StudentBillingProcessingShell>
    );
  }

  if (processing.pageState === "expired") {
    return (
      <StudentBillingProcessingShell
        eyebrow="Billing update"
        title="This order expired"
        description="The order can no longer be completed."
        orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
      >
        <StudentBillingProcessingTerminalState
          variant="expired"
          onGoBack={handleGoBack}
        />
      </StudentBillingProcessingShell>
    );
  }

  if (
    processing.pageState === "pending_manual_verification" ||
    processing.pageState === "recoverable_error"
  ) {
    return (
      <StudentBillingProcessingShell
        eyebrow="Billing verification"
        title="We are still checking this payment"
        description="This payment needs another verification pass before we can show the final result."
        orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
      >
        <StudentBillingProcessingManualReviewState
          onRetry={() => void processing.retryStatusCheck()}
          onGoBack={handleGoBack}
        />
      </StudentBillingProcessingShell>
    );
  }

  if (processing.pageState === "awaiting_confirmation") {
    return (
      <StudentBillingProcessingShell
        eyebrow="Billing verification"
        title="Verifying your payment"
        description="Please stay on this page while we confirm settlement from the backend."
        orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
      >
        <StudentBillingProcessingPendingState
          creditAmount={orderStatus?.credit_amount}
          amountLabel={amountLabel}
          packageCode={orderStatus?.package_code}
        />
      </StudentBillingProcessingShell>
    );
  }

  return (
    <StudentBillingProcessingShell
      eyebrow="Billing verification"
      title="Verifying your payment"
      description="Please wait while we securely validate your billing order."
      orderRef={orderStatus?.merchant_order_ref ?? paymentOrderId}
    >
      <StudentBillingProcessingLoadingState />
    </StudentBillingProcessingShell>
  );
}