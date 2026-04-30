"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { getStudentBillingOverview } from "../api/student-billing-api";
import { STUDENT_BILLING_QUERY_KEYS } from "../constants/student-billing-ui";
import type { StudentBillingOverviewResponse } from "../types/student-billing-contracts";
import type { BillingOverviewViewModel } from "../types/student-billing-view-models";
import {
  buildBillingLowCreditState,
  buildBillingPackageCardViewModels,
} from "../utils/student-billing-package-view-models";

type UseStudentBillingOverviewOptions = {
  accessToken: string | null;
  enabled?: boolean;
};

type UseStudentBillingOverviewResult = {
  overview: StudentBillingOverviewResponse | null;
  viewModel: BillingOverviewViewModel | null;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<unknown>;
};

export function useStudentBillingOverview({
  accessToken,
  enabled = true,
}: UseStudentBillingOverviewOptions): UseStudentBillingOverviewResult {
  const query = useQuery({
    queryKey: STUDENT_BILLING_QUERY_KEYS.overview,
    queryFn: async () => {
      if (!accessToken) {
        throw new Error("SESSION_EXPIRED");
      }

      return getStudentBillingOverview(accessToken);
    },
    enabled: enabled && Boolean(accessToken),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 1,
  });

  const viewModel = useMemo<BillingOverviewViewModel | null>(() => {
    const overview = query.data;
    if (!overview) {
      return null;
    }

    return {
      wallet: overview.wallet,
      lowCreditState: buildBillingLowCreditState(
        overview.wallet.available_credits,
      ),
      recentTransactions: overview.recent_transactions,
      recentLedgerEntries: overview.recent_ledger_entries,
      packages: buildBillingPackageCardViewModels(overview.packages),
    };
  }, [query.data]);

  return {
    overview: query.data ?? null,
    viewModel,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error instanceof Error ? query.error : null,
    refetch: query.refetch,
  };
}