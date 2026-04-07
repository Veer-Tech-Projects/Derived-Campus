"use client";

import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

type QueryProviderProps = {
  children: React.ReactNode;
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        /**
         * Global default only.
         * Feature-level hooks may override this where needed.
         */
        staleTime: 60 * 1000,

        /**
         * Prevent noisy background refetches that can create confusing UX
         * and unnecessary backend load for data-heavy enterprise flows.
         */
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        refetchOnMount: false,

        /**
         * Keep query errors explicit. Do not blindly retry by default,
         * especially for validation/domain errors or controlled student flows.
         * If a specific feature needs retries, it should opt in locally.
         */
        retry: false,

        /**
         * Avoid suspense assumptions at the global layer.
         * Features can opt into their own loading strategy.
         */
        gcTime: 5 * 60 * 1000,
      },
      mutations: {
        /**
         * Mutations should also fail fast by default.
         * Feature-specific retry behavior must be intentional.
         */
        retry: false,
      },
    },
  });
}

export function QueryProvider({ children }: QueryProviderProps) {
  /**
   * Ensures the QueryClient is created exactly once per browser session
   * for this mounted provider instance.
   */
  const [queryClient] = useState(createQueryClient);

  const isDevelopment = process.env.NODE_ENV === "development";

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {isDevelopment ? <ReactQueryDevtools initialIsOpen={false} /> : null}
    </QueryClientProvider>
  );
}