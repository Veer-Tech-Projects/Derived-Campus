"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { useStudentBillingOrderStatus } from "./use-student-billing-order-status";
import {
  STUDENT_BILLING_QUERY_KEYS,
  STUDENT_BILLING_SETTLED_STATUS,
} from "../constants/student-billing-ui";
import type { StudentBillingOrderStatusResponse } from "../types/student-billing-contracts";
import type { BillingPurchaseLifecycleStatus } from "../types/student-billing-view-models";

export type StudentBillingProcessingPageState =
  | "loading"
  | "awaiting_confirmation"
  | "settled"
  | "failed"
  | "cancelled"
  | "expired"
  | "pending_manual_verification"
  | "recoverable_error";

type UseStudentBillingProcessingStatusOptions = {
  accessToken: string | null;
  paymentOrderId: string;
  redirectTo?: string;
};

type UseStudentBillingProcessingStatusResult = {
  orderStatus: StudentBillingOrderStatusResponse | null;
  lifecycleStatus: BillingPurchaseLifecycleStatus;
  pageState: StudentBillingProcessingPageState;
  isInitialLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  countdownSeconds: number;
  retryStatusCheck: () => Promise<void>;
  redirectNow: () => void;
};

const SUCCESS_REDIRECT_SECONDS = 5;

function mapLifecycleToPageState(
  lifecycleStatus: BillingPurchaseLifecycleStatus,
  hasRecoverableError: boolean,
): StudentBillingProcessingPageState {
  if (hasRecoverableError) {
    return "recoverable_error";
  }

  switch (lifecycleStatus) {
    case "settled":
      return "settled";
    case "failed":
      return "failed";
    case "cancelled":
      return "cancelled";
    case "expired":
      return "expired";
    case "pending_manual_verification":
      return "pending_manual_verification";
    case "idle":
    case "creating_order":
    case "opening_checkout":
      return "loading";
    case "awaiting_backend_confirmation":
    default:
      return "awaiting_confirmation";
  }
}

export function useStudentBillingProcessingStatus({
  accessToken,
  paymentOrderId,
  redirectTo = "/student-account",
}: UseStudentBillingProcessingStatusOptions): UseStudentBillingProcessingStatusResult {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [countdownSeconds, setCountdownSeconds] = useState(SUCCESS_REDIRECT_SECONDS);
  const redirectTriggeredRef = useRef(false);
  const settlementSyncCompletedRef = useRef(false);

  const orderStatusState = useStudentBillingOrderStatus({
    accessToken,
    paymentOrderId,
    enabled: Boolean(accessToken && paymentOrderId),
    autoStartPolling: true,
  });

  const {
    orderStatus,
    lifecycleStatus,
    isLoading,
    isFetching,
    error,
    refetch,
    isPolling,
    startPolling,
  } = orderStatusState;

  const pageState = useMemo<StudentBillingProcessingPageState>(() => {
    const noDataYet = !orderStatus && !error && (isLoading || isFetching);
    if (noDataYet) {
      return "loading";
    }

    return mapLifecycleToPageState(lifecycleStatus, Boolean(error));
  }, [error, isFetching, isLoading, lifecycleStatus, orderStatus]);

  const redirectNow = useCallback(() => {
    if (redirectTriggeredRef.current) {
      return;
    }

    redirectTriggeredRef.current = true;
    router.replace(redirectTo);
  }, [redirectTo, router]);

  const retryStatusCheck = useCallback(async () => {
    await refetch();

    if (!isPolling && accessToken && paymentOrderId) {
      startPolling();
    }
  }, [accessToken, isPolling, paymentOrderId, refetch, startPolling]);


  useEffect(() => {
    if (pageState !== "settled") {
      settlementSyncCompletedRef.current = false;
      return;
    }

    if (settlementSyncCompletedRef.current) {
      return;
    }

    settlementSyncCompletedRef.current = true;

    void (async () => {
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
        queryClient.refetchQueries({
          queryKey: STUDENT_BILLING_QUERY_KEYS.overview,
          type: "active",
        }),
        queryClient.refetchQueries({
          queryKey: STUDENT_BILLING_QUERY_KEYS.transactions(20).slice(0, 1),
          type: "active",
        }),
        queryClient.refetchQueries({
          queryKey: STUDENT_BILLING_QUERY_KEYS.ledger(20).slice(0, 1),
          type: "active",
        }),
      ]);
    })();
  }, [pageState, queryClient]);

  useEffect(() => {
    if (pageState !== "settled") {
      setCountdownSeconds(SUCCESS_REDIRECT_SECONDS);
      redirectTriggeredRef.current = false;
      return;
    }

    if (orderStatus?.status !== STUDENT_BILLING_SETTLED_STATUS) {
      return;
    }

    if (countdownSeconds <= 0) {
      redirectNow();
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setCountdownSeconds((current) => current - 1);
    }, 1000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [countdownSeconds, orderStatus?.status, pageState, redirectNow]);

  return {
    orderStatus,
    lifecycleStatus,
    pageState,
    isInitialLoading: isLoading && !orderStatus,
    isFetching,
    error: error ?? null,
    countdownSeconds,
    retryStatusCheck,
    redirectNow,
  };
}