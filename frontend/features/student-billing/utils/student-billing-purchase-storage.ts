import {
  STUDENT_BILLING_FINAL_FAILURE_STATUSES,
  STUDENT_BILLING_SETTLED_STATUS,
  STUDENT_BILLING_STORAGE_KEYS,
} from "../constants/student-billing-ui";
import type { BillingPurchaseSessionSnapshot } from "../types/student-billing-view-models";

const PURCHASE_SESSION_MAX_AGE_MS = 30 * 60 * 1000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isValidPurchaseSessionSnapshot(
  value: unknown,
): value is BillingPurchaseSessionSnapshot {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.paymentOrderId === "string" &&
    value.paymentOrderId.length > 0 &&
    typeof value.merchantOrderRef === "string" &&
    value.merchantOrderRef.length > 0 &&
    typeof value.packageCode === "string" &&
    value.packageCode.length > 0 &&
    typeof value.clientIdempotencyKey === "string" &&
    value.clientIdempotencyKey.length > 0 &&
    typeof value.createdAt === "string" &&
    value.createdAt.length > 0 &&
    typeof value.lastKnownStatus === "string" &&
    value.lastKnownStatus.length > 0
  );
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function isExpiredPurchaseSession(
  snapshot: BillingPurchaseSessionSnapshot,
): boolean {
  const createdAtMs = new Date(snapshot.createdAt).getTime();

  if (Number.isNaN(createdAtMs)) {
    return true;
  }

  return Date.now() - createdAtMs > PURCHASE_SESSION_MAX_AGE_MS;
}

export function readStudentBillingPurchaseSession():
  | BillingPurchaseSessionSnapshot
  | null {
  if (!canUseStorage()) {
    return null;
  }

  const rawValue = window.localStorage.getItem(
    STUDENT_BILLING_STORAGE_KEYS.purchaseSession,
  );

  if (!rawValue) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(rawValue);

    if (!isValidPurchaseSessionSnapshot(parsed)) {
      clearStudentBillingPurchaseSession();
      return null;
    }

    if (isExpiredPurchaseSession(parsed)) {
      clearStudentBillingPurchaseSession();
      return null;
    }

    return parsed;
  } catch {
    clearStudentBillingPurchaseSession();
    return null;
  }
}

export function writeStudentBillingPurchaseSession(
  value: BillingPurchaseSessionSnapshot,
): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(
    STUDENT_BILLING_STORAGE_KEYS.purchaseSession,
    JSON.stringify(value),
  );
}

export function updateStudentBillingPurchaseSessionStatus(
  nextStatus: string,
): BillingPurchaseSessionSnapshot | null {
  const existing = readStudentBillingPurchaseSession();
  if (!existing) {
    return null;
  }

  const nextValue: BillingPurchaseSessionSnapshot = {
    ...existing,
    lastKnownStatus: nextStatus,
  };

  writeStudentBillingPurchaseSession(nextValue);
  return nextValue;
}

export function clearStudentBillingPurchaseSession(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(STUDENT_BILLING_STORAGE_KEYS.purchaseSession);
}

export function shouldReuseStoredPurchaseSession(
  snapshot: BillingPurchaseSessionSnapshot | null,
): snapshot is BillingPurchaseSessionSnapshot {
  if (!snapshot) {
    return false;
  }

  if (isExpiredPurchaseSession(snapshot)) {
    return false;
  }

  if (snapshot.lastKnownStatus === STUDENT_BILLING_SETTLED_STATUS) {
    return false;
  }

  if (STUDENT_BILLING_FINAL_FAILURE_STATUSES.has(snapshot.lastKnownStatus)) {
    return false;
  }

  return true;
}

export function shouldRotateIdempotencyKeyForStatus(status: string): boolean {
  return STUDENT_BILLING_FINAL_FAILURE_STATUSES.has(status);
}