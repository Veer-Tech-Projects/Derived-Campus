import type {
  CreditLedgerListResponse,
  CreditPackageListResponse,
  PaymentTransactionListResponse,
  StudentBillingCreateOrderRequest,
  StudentBillingCreateOrderResponse,
  StudentBillingOrderStatusResponse,
  StudentBillingOverviewResponse,
} from "../types/student-billing-contracts";

function getStudentBillingApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_URL;

  if (!value) {
    throw new Error(
      "FATAL: NEXT_PUBLIC_API_URL is missing for student billing API.",
    );
  }

  return value.replace(/\/+$/, "");
}

function buildAuthHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

async function parseJsonOrThrow<T>(response: Response): Promise<T> {
  const text = await response.text();

  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    if (
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      if (response.status === 401) {
        throw new Error("SESSION_EXPIRED");
      }
      throw new Error(payload.detail);
    }

    if (response.status === 401) {
      throw new Error("SESSION_EXPIRED");
    }

    if (typeof payload === "string" && payload.trim().length > 0) {
      throw new Error(payload);
    }

    throw new Error(`Billing request failed with status ${response.status}.`);
  }

  return payload as T;
}

export async function getStudentBillingOverview(
  accessToken: string,
): Promise<StudentBillingOverviewResponse> {
  const response = await fetch(
    `${getStudentBillingApiBaseUrl()}/student-billing/overview`,
    {
      method: "GET",
      credentials: "include",
      headers: buildAuthHeaders(accessToken),
      cache: "no-store",
    },
  );

  return parseJsonOrThrow<StudentBillingOverviewResponse>(response);
}

export async function getStudentBillingPackages(
  accessToken: string,
): Promise<CreditPackageListResponse> {
  const response = await fetch(
    `${getStudentBillingApiBaseUrl()}/student-billing/packages`,
    {
      method: "GET",
      credentials: "include",
      headers: buildAuthHeaders(accessToken),
      cache: "no-store",
    },
  );

  return parseJsonOrThrow<CreditPackageListResponse>(response);
}

export async function createStudentBillingOrder(
  accessToken: string,
  payload: StudentBillingCreateOrderRequest,
): Promise<StudentBillingCreateOrderResponse> {
  const response = await fetch(
    `${getStudentBillingApiBaseUrl()}/student-billing/orders`,
    {
      method: "POST",
      credentials: "include",
      headers: buildAuthHeaders(accessToken),
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );

  return parseJsonOrThrow<StudentBillingCreateOrderResponse>(response);
}

export async function getStudentBillingOrderStatus(
  accessToken: string,
  paymentOrderId: string,
): Promise<StudentBillingOrderStatusResponse> {
  const response = await fetch(
    `${getStudentBillingApiBaseUrl()}/student-billing/orders/${paymentOrderId}`,
    {
      method: "GET",
      credentials: "include",
      headers: buildAuthHeaders(accessToken),
      cache: "no-store",
    },
  );

  return parseJsonOrThrow<StudentBillingOrderStatusResponse>(response);
}

export async function getStudentBillingTransactions(
  accessToken: string,
  limit = 20,
): Promise<PaymentTransactionListResponse> {
  const response = await fetch(
    `${getStudentBillingApiBaseUrl()}/student-billing/transactions?limit=${limit}`,
    {
      method: "GET",
      credentials: "include",
      headers: buildAuthHeaders(accessToken),
      cache: "no-store",
    },
  );

  return parseJsonOrThrow<PaymentTransactionListResponse>(response);
}

export async function getStudentBillingLedger(
  accessToken: string,
  limit = 20,
): Promise<CreditLedgerListResponse> {
  const response = await fetch(
    `${getStudentBillingApiBaseUrl()}/student-billing/ledger?limit=${limit}`,
    {
      method: "GET",
      credentials: "include",
      headers: buildAuthHeaders(accessToken),
      cache: "no-store",
    },
  );

  return parseJsonOrThrow<CreditLedgerListResponse>(response);
}