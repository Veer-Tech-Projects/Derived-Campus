"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getStudentBillingOrderStatus } from "../api/student-billing-api";
import {
  STUDENT_BILLING_ACTIVE_ORDER_STATUSES,
  STUDENT_BILLING_FINAL_FAILURE_STATUSES,
  STUDENT_BILLING_POLLING,
  STUDENT_BILLING_QUERY_KEYS,
  STUDENT_BILLING_SETTLED_STATUS,
} from "../constants/student-billing-ui";
import type { StudentBillingOrderStatusResponse } from "../types/student-billing-contracts";
import type { BillingPurchaseLifecycleStatus } from "../types/student-billing-view-models";

type UseStudentBillingOrderStatusOptions = {
  accessToken: string | null;
  paymentOrderId: string | null;
  enabled?: boolean;
  autoStartPolling?: boolean;
};

type UseStudentBillingOrderStatusResult = {
  orderStatus: StudentBillingOrderStatusResponse | null;
  lifecycleStatus: BillingPurchaseLifecycleStatus;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  error: Error | null;
  isPolling: boolean;
  pollTimedOut: boolean;
  startPolling: () => void;
  stopPolling: () => void;
  refetch: () => Promise<unknown>;
};

function computeNextIntervalMs(previousMs: number): number {
  const nextMs = Math.ceil(
    previousMs * STUDENT_BILLING_POLLING.backoffMultiplier,
  );

  return Math.min(nextMs, STUDENT_BILLING_POLLING.maxIntervalMs);
}

function mapBackendOrderStatusToLifecycle(
  backendStatus: string | null | undefined,
): BillingPurchaseLifecycleStatus {
  if (!backendStatus) {
    return "idle";
  }

  if (backendStatus === STUDENT_BILLING_SETTLED_STATUS) {
    return "settled";
  }

  if (backendStatus === "FAILED") {
    return "failed";
  }

  if (backendStatus === "CANCELLED") {
    return "cancelled";
  }

  if (backendStatus === "EXPIRED") {
    return "expired";
  }

  if (backendStatus === "CREATED") {
    return "creating_order";
  }

  if (backendStatus === "GATEWAY_ORDER_CREATED") {
    return "opening_checkout";
  }

  if (backendStatus === "CHECKOUT_INITIATED") {
    return "awaiting_backend_confirmation";
  }

  return "awaiting_backend_confirmation";
}

export function useStudentBillingOrderStatus({
  accessToken,
  paymentOrderId,
  enabled = true,
  autoStartPolling = false,
}: UseStudentBillingOrderStatusOptions): UseStudentBillingOrderStatusResult {
  const queryClient = useQueryClient();

  const [isPolling, setIsPolling] = useState(autoStartPolling);
  const [pollTimedOut, setPollTimedOut] = useState(false);

  const pollStartedAtRef = useRef<number | null>(null);
  const currentIntervalMsRef = useRef<number>(
    STUDENT_BILLING_POLLING.initialIntervalMs,
  );
  const timeoutHandleRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearScheduledPoll = useCallback(() => {
    if (timeoutHandleRef.current) {
      clearTimeout(timeoutHandleRef.current);
      timeoutHandleRef.current = null;
    }
  }, []);

  const resetPollingWindow = useCallback(() => {
    pollStartedAtRef.current = null;
    currentIntervalMsRef.current = STUDENT_BILLING_POLLING.initialIntervalMs;
    setPollTimedOut(false);
  }, []);

  const stopPolling = useCallback(() => {
    clearScheduledPoll();
    setIsPolling(false);
    resetPollingWindow();
  }, [clearScheduledPoll, resetPollingWindow]);

  const query = useQuery({
    queryKey:
      paymentOrderId && enabled
        ? STUDENT_BILLING_QUERY_KEYS.orderStatus(paymentOrderId)
        : ["student-billing-order-status", "disabled"],
    queryFn: async () => {
      if (!accessToken) {
        throw new Error("SESSION_EXPIRED");
      }

      if (!paymentOrderId) {
        throw new Error("Missing payment order id.");
      }

      return getStudentBillingOrderStatus(accessToken, paymentOrderId);
    },
    enabled: enabled && Boolean(accessToken) && Boolean(paymentOrderId),
    staleTime: 0,
    gcTime: 10 * 60_000,
    retry: 1,
  });

  const { refetch } = query;
  const backendStatus = query.data?.status ?? null;

  const lifecycleStatus = useMemo<BillingPurchaseLifecycleStatus>(() => {
    if (pollTimedOut) {
      return "pending_manual_verification";
    }

    return mapBackendOrderStatusToLifecycle(backendStatus);
  }, [backendStatus, pollTimedOut]);

  const scheduleNextPoll = useCallback(() => {
    if (!isPolling || !paymentOrderId) {
      return;
    }

    const now = Date.now();
    if (pollStartedAtRef.current === null) {
      pollStartedAtRef.current = now;
    }

    const elapsedMs = now - pollStartedAtRef.current;
    if (elapsedMs >= STUDENT_BILLING_POLLING.hardTimeoutMs) {
      clearScheduledPoll();
      setIsPolling(false);
      setPollTimedOut(true);
      return;
    }

    clearScheduledPoll();

    timeoutHandleRef.current = setTimeout(async () => {
      await refetch();

      currentIntervalMsRef.current = computeNextIntervalMs(
        currentIntervalMsRef.current,
      );

      scheduleNextPoll();
    }, currentIntervalMsRef.current);
  }, [clearScheduledPoll, isPolling, paymentOrderId, refetch]);

  const startPolling = useCallback(() => {
    if (!paymentOrderId) {
      return;
    }

    clearScheduledPoll();
    setPollTimedOut(false);
    setIsPolling(true);
    pollStartedAtRef.current = Date.now();
    currentIntervalMsRef.current = STUDENT_BILLING_POLLING.initialIntervalMs;
  }, [clearScheduledPoll, paymentOrderId]);

  useEffect(() => {
    if (!isPolling) {
      clearScheduledPoll();
      return;
    }

    if (!paymentOrderId || !enabled || !accessToken) {
      stopPolling();
      return;
    }

    const currentStatus = query.data?.status;

    if (currentStatus === STUDENT_BILLING_SETTLED_STATUS) {
      clearScheduledPoll();
      setIsPolling(false);

      void queryClient.invalidateQueries({
        queryKey: STUDENT_BILLING_QUERY_KEYS.overview,
      });
      void queryClient.invalidateQueries({
        queryKey: STUDENT_BILLING_QUERY_KEYS.transactions(20).slice(0, 1),
      });
      void queryClient.invalidateQueries({
        queryKey: STUDENT_BILLING_QUERY_KEYS.ledger(20).slice(0, 1),
      });
      return;
    }

    if (
      currentStatus &&
      STUDENT_BILLING_FINAL_FAILURE_STATUSES.has(currentStatus)
    ) {
      clearScheduledPoll();
      setIsPolling(false);
      return;
    }

    if (
      currentStatus &&
      !STUDENT_BILLING_ACTIVE_ORDER_STATUSES.has(currentStatus) &&
      currentStatus !== STUDENT_BILLING_SETTLED_STATUS
    ) {
      clearScheduledPoll();
      setIsPolling(false);
      return;
    }

    scheduleNextPoll();

    return () => {
      clearScheduledPoll();
    };
  }, [
    accessToken,
    clearScheduledPoll,
    enabled,
    isPolling,
    paymentOrderId,
    query.data?.status,
    queryClient,
    scheduleNextPoll,
    stopPolling,
  ]);

  useEffect(() => {
    if (!autoStartPolling) {
      return;
    }

    if (paymentOrderId && enabled) {
      startPolling();
    }
  }, [autoStartPolling, enabled, paymentOrderId, startPolling]);

  useEffect(() => {
    return () => {
      clearScheduledPoll();
    };
  }, [clearScheduledPoll]);

  return {
    orderStatus: query.data ?? null,
    lifecycleStatus,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error instanceof Error ? query.error : null,
    isPolling,
    pollTimedOut,
    startPolling,
    stopPolling,
    refetch,
  };
}