"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  createStudentBillingOrder,
  getStudentBillingOrderStatus,
} from "../api/student-billing-api";
import {
  STUDENT_BILLING_FINAL_FAILURE_STATUSES,
  STUDENT_BILLING_QUERY_KEYS,
  STUDENT_BILLING_SETTLED_STATUS,
} from "../constants/student-billing-ui";
import type {
  CreditPackageDTO,
  StudentBillingOrderStatusResponse,
} from "../types/student-billing-contracts";
import type {
  BillingPurchaseLifecycleStatus,
  BillingPurchaseSessionSnapshot,
  BillingStatusBannerState,
} from "../types/student-billing-view-models";
import {
  clearStudentBillingPurchaseSession,
  readStudentBillingPurchaseSession,
  shouldRotateIdempotencyKeyForStatus,
  shouldReuseStoredPurchaseSession,
  updateStudentBillingPurchaseSessionStatus,
  writeStudentBillingPurchaseSession,
} from "../utils/student-billing-purchase-storage";
import { useRazorpayCheckout } from "./use-razorpay-checkout";
import { useStudentBillingOrderStatus } from "./use-student-billing-order-status";

type UseStudentBillingPurchaseOptions = {
  accessToken: string | null;
};

type BeginPurchaseInput = {
  selectedPackage: CreditPackageDTO;
};

type UseStudentBillingPurchaseResult = {
  lifecycleStatus: BillingPurchaseLifecycleStatus;
  activePaymentOrderId: string | null;
  activePackageCode: string | null;
  activeBannerState: BillingStatusBannerState;
  isBusy: boolean;
  beginPurchase: (input: BeginPurchaseInput) => Promise<void>;
  recoverPersistedPurchase: () => Promise<void>;
  clearPurchaseState: () => void;
};

function buildClientIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `billing-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function toBannerState(
  lifecycleStatus: BillingPurchaseLifecycleStatus,
): BillingStatusBannerState {
  switch (lifecycleStatus) {
    case "creating_order":
      return {
        visible: true,
        tone: "info",
        title: "Creating secure billing order",
        description: "Please wait while we prepare your purchase.",
      };

    case "opening_checkout":
      return {
        visible: true,
        tone: "info",
        title: "Opening secure checkout",
        description: "Please continue in the Razorpay window.",
      };

    case "awaiting_backend_confirmation":
      return {
        visible: true,
        tone: "warning",
        title: "Awaiting payment confirmation",
        description:
          "Your credits will update automatically after backend verification.",
      };

    case "settled":
      return {
        visible: true,
        tone: "success",
        title: "Credits added successfully",
        description:
          "Your wallet has been refreshed using backend-confirmed payment status.",
      };

    case "failed":
      return {
        visible: true,
        tone: "danger",
        title: "Purchase failed",
        description: "You can retry securely with a fresh billing order.",
      };

    case "cancelled":
      return {
        visible: true,
        tone: "warning",
        title: "Checkout closed",
        description:
          "No backend-confirmed payment was detected. You can start a new purchase when ready.",
      };

    case "expired":
      return {
        visible: true,
        tone: "warning",
        title: "Order expired",
        description: "Please create a new billing order to continue.",
      };

    case "pending_manual_verification":
      return {
        visible: true,
        tone: "warning",
        title: "Payment pending verification",
        description:
          "We could not confirm settlement yet. Please check back shortly.",
      };

    default:
      return {
        visible: false,
        tone: "neutral",
        title: "",
      };
  }
}

function isTerminalBackendStatus(status: string): boolean {
  return (
    status === STUDENT_BILLING_SETTLED_STATUS ||
    STUDENT_BILLING_FINAL_FAILURE_STATUSES.has(status)
  );
}

function hasBackendConfirmationProgress(status: string): boolean {
  return status === "CHECKOUT_INITIATED";
}

export function useStudentBillingPurchase({
  accessToken,
}: UseStudentBillingPurchaseOptions): UseStudentBillingPurchaseResult {
  const queryClient = useQueryClient();

  const razorpayCheckout = useRazorpayCheckout();

  const [lifecycleStatus, setLifecycleStatus] =
    useState<BillingPurchaseLifecycleStatus>("idle");
  const [activePaymentOrderId, setActivePaymentOrderId] = useState<string | null>(
    null,
  );
  const [activePackageCode, setActivePackageCode] = useState<string | null>(null);

  const paymentCompletionSignaledRef = useRef(false);

  const orderStatusState = useStudentBillingOrderStatus({
    accessToken,
    paymentOrderId: activePaymentOrderId,
    enabled: Boolean(accessToken && activePaymentOrderId),
    autoStartPolling: false,
  });

  const {
    orderStatus: latestOrderStatus,
    pollTimedOut,
    startPolling,
    stopPolling,
    isFetching: isOrderStatusFetching,
    isPolling,
  } = orderStatusState;

  const syncCachesAfterSettlement = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: STUDENT_BILLING_QUERY_KEYS.overview,
      }),
      queryClient.invalidateQueries({
        queryKey: STUDENT_BILLING_QUERY_KEYS.transactions(20).slice(0, 1),
      }),
      queryClient.invalidateQueries({
        queryKey: STUDENT_BILLING_QUERY_KEYS.ledger(20).slice(0, 1),
      }),
    ]);
  }, [queryClient]);

  const resetPaymentSignal = useCallback(() => {
    paymentCompletionSignaledRef.current = false;
  }, []);

  const clearPurchaseState = useCallback(() => {
    clearStudentBillingPurchaseSession();
    setLifecycleStatus("idle");
    setActivePaymentOrderId(null);
    setActivePackageCode(null);
    stopPolling();
    resetPaymentSignal();
  }, [resetPaymentSignal, stopPolling]);

  const handleBackendStatusTransition = useCallback(
    async (status: string) => {
      updateStudentBillingPurchaseSessionStatus(status);

      if (status === STUDENT_BILLING_SETTLED_STATUS) {
        setLifecycleStatus("settled");
        await syncCachesAfterSettlement();
        clearStudentBillingPurchaseSession();
        stopPolling();
        resetPaymentSignal();
        return;
      }

      if (STUDENT_BILLING_FINAL_FAILURE_STATUSES.has(status)) {
        if (status === "FAILED") {
          setLifecycleStatus("failed");
        } else if (status === "CANCELLED") {
          setLifecycleStatus("cancelled");
        } else if (status === "EXPIRED") {
          setLifecycleStatus("expired");
        }

        clearStudentBillingPurchaseSession();
        stopPolling();
        resetPaymentSignal();
        return;
      }

      setLifecycleStatus("awaiting_backend_confirmation");
    },
    [resetPaymentSignal, stopPolling, syncCachesAfterSettlement],
  );

  const reconcileOrderStatusOnce = useCallback(
    async (
      paymentOrderId: string,
    ): Promise<StudentBillingOrderStatusResponse | null> => {
      if (!accessToken) {
        return null;
      }

      try {
        return await getStudentBillingOrderStatus(accessToken, paymentOrderId);
      } catch {
        return null;
      }
    },
    [accessToken],
  );

  const recoverPersistedPurchase = useCallback(async () => {
    const stored = readStudentBillingPurchaseSession();

    if (!shouldReuseStoredPurchaseSession(stored)) {
      clearPurchaseState();
      return;
    }

    setActivePaymentOrderId(stored.paymentOrderId);
    setActivePackageCode(stored.packageCode);

    const latest = await reconcileOrderStatusOnce(stored.paymentOrderId);

    if (!latest) {
      setLifecycleStatus("awaiting_backend_confirmation");
      startPolling();
      return;
    }

    if (isTerminalBackendStatus(latest.status)) {
      await handleBackendStatusTransition(latest.status);
      return;
    }

    if (
      hasBackendConfirmationProgress(latest.status) ||
      stored.lastKnownStatus === "CHECKOUT_INITIATED" ||
      stored.lastKnownStatus === "awaiting_backend_confirmation"
    ) {
      updateStudentBillingPurchaseSessionStatus(latest.status);
      setLifecycleStatus("awaiting_backend_confirmation");
      startPolling();
      return;
    }

    clearPurchaseState();
  }, [
    clearPurchaseState,
    handleBackendStatusTransition,
    reconcileOrderStatusOnce,
    startPolling,
  ]);

  const beginPurchase = useCallback(
    async ({ selectedPackage }: BeginPurchaseInput) => {
      if (!accessToken) {
        throw new Error("SESSION_EXPIRED");
      }

      resetPaymentSignal();

      const existingSnapshot = readStudentBillingPurchaseSession();

      const nextIdempotencyKey =
        existingSnapshot &&
        !shouldRotateIdempotencyKeyForStatus(existingSnapshot.lastKnownStatus)
          ? existingSnapshot.clientIdempotencyKey
          : buildClientIdempotencyKey();

      setLifecycleStatus("creating_order");
      setActivePackageCode(selectedPackage.package_code);

      const order = await createStudentBillingOrder(accessToken, {
        package_code: selectedPackage.package_code,
        client_idempotency_key: nextIdempotencyKey,
      });

      const snapshot: BillingPurchaseSessionSnapshot = {
        paymentOrderId: order.payment_order_id,
        merchantOrderRef: order.merchant_order_ref,
        packageCode: selectedPackage.package_code,
        clientIdempotencyKey: nextIdempotencyKey,
        createdAt: new Date().toISOString(),
        lastKnownStatus: order.status,
      };

      writeStudentBillingPurchaseSession(snapshot);
      setActivePaymentOrderId(order.payment_order_id);

      if (order.status === "GATEWAY_ORDER_CREATED" && order.gateway_order_id) {
        setLifecycleStatus("opening_checkout");

        const checkoutOpened = await razorpayCheckout.openCheckout({
          key: order.checkout_public_key,
          orderId: order.gateway_order_id,
          amountMinor: order.amount_minor,
          currencyCode: order.currency_code,
          merchantOrderRef: order.merchant_order_ref,
          prefillName: order.checkout_prefill_name,
          prefillEmail: order.checkout_prefill_email,
          onPaymentCompleted: () => {
            paymentCompletionSignaledRef.current = true;
            updateStudentBillingPurchaseSessionStatus("CHECKOUT_INITIATED");
            setLifecycleStatus("awaiting_backend_confirmation");
            startPolling();
            window.location.replace(
              `/student-billing/processing/${order.payment_order_id}`,
            );
          },
          onDismiss: () => {
            const currentPaymentOrderId = order.payment_order_id;

            void (async () => {
              const latest = await reconcileOrderStatusOnce(currentPaymentOrderId);

              if (latest && isTerminalBackendStatus(latest.status)) {
                await handleBackendStatusTransition(latest.status);
                return;
              }

              if (
                paymentCompletionSignaledRef.current ||
                (latest && hasBackendConfirmationProgress(latest.status))
              ) {
                updateStudentBillingPurchaseSessionStatus(
                  latest?.status ?? "CHECKOUT_INITIATED",
                );
                setLifecycleStatus("awaiting_backend_confirmation");
                startPolling();
                return;
              }

              updateStudentBillingPurchaseSessionStatus("CANCELLED");
              clearStudentBillingPurchaseSession();
              setLifecycleStatus("cancelled");
              stopPolling();
              resetPaymentSignal();
            })();
          },
          onPaymentFailed: () => {
            const currentPaymentOrderId = order.payment_order_id;

            void (async () => {
              const latest = await reconcileOrderStatusOnce(currentPaymentOrderId);

              if (latest && isTerminalBackendStatus(latest.status)) {
                await handleBackendStatusTransition(latest.status);
                return;
              }

              updateStudentBillingPurchaseSessionStatus("FAILED");
              clearStudentBillingPurchaseSession();
              setLifecycleStatus("failed");
              stopPolling();
              resetPaymentSignal();
            })();
          },
        });

        if (!checkoutOpened) {
          updateStudentBillingPurchaseSessionStatus("FAILED");
          clearStudentBillingPurchaseSession();
          setLifecycleStatus("failed");
          stopPolling();
          resetPaymentSignal();
          return;
        }

        return;
      }

      setLifecycleStatus("awaiting_backend_confirmation");
      startPolling();
    },
    [
      accessToken,
      handleBackendStatusTransition,
      razorpayCheckout,
      reconcileOrderStatusOnce,
      resetPaymentSignal,
      startPolling,
      stopPolling,
    ],
  );

  useEffect(() => {
    if (!latestOrderStatus?.status) {
      return;
    }

    if (!isPolling && !isTerminalBackendStatus(latestOrderStatus.status)) {
      return;
    }

    void handleBackendStatusTransition(latestOrderStatus.status);
  }, [handleBackendStatusTransition, isPolling, latestOrderStatus?.status]);

  useEffect(() => {
    if (!pollTimedOut) {
      return;
    }

    setLifecycleStatus("pending_manual_verification");
  }, [pollTimedOut]);

  const activeBannerState = useMemo(
    () => toBannerState(lifecycleStatus),
    [lifecycleStatus],
  );

  const isBusy =
    lifecycleStatus === "creating_order" ||
    lifecycleStatus === "opening_checkout" ||
    lifecycleStatus === "awaiting_backend_confirmation" ||
    isOrderStatusFetching ||
    razorpayCheckout.isScriptLoading;

  return {
    lifecycleStatus,
    activePaymentOrderId,
    activePackageCode,
    activeBannerState,
    isBusy,
    beginPurchase,
    recoverPersistedPurchase,
    clearPurchaseState,
  };
}