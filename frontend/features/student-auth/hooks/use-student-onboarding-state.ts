"use client";

import { useCallback, useEffect, useState } from "react";

import { getStudentOnboardingState } from "../api/student-auth-api";
import { useStudentAuth } from "./use-student-auth";
import type { StudentOnboardingStateResponse } from "../types/student-auth-contracts";
import type { StudentOnboardingViewState } from "../types/student-auth-view-models";

const initialState: StudentOnboardingViewState = {
  onboardingRequired: false,
  onboardingState: null,
  loading: false,
  errorMessage: null,
};

export function useStudentOnboardingState() {
  const { accessToken, status } = useStudentAuth();
  const [state, setState] = useState<StudentOnboardingViewState>(initialState);

  const load = useCallback(async () => {
    if (!accessToken) {
      setState({
        onboardingRequired: false,
        onboardingState: null,
        loading: false,
        errorMessage: "No student access token is available.",
      });
      return;
    }

    setState((prev) => ({
      ...prev,
      loading: true,
      errorMessage: null,
    }));

    try {
      const response: StudentOnboardingStateResponse =
        await getStudentOnboardingState(accessToken);

      setState({
        onboardingRequired: response.onboarding_required,
        onboardingState: response,
        loading: false,
        errorMessage: null,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to load onboarding state.";

      setState({
        onboardingRequired: false,
        onboardingState: null,
        loading: false,
        errorMessage: message,
      });
    }
  }, [accessToken]);

  useEffect(() => {
    if (status === "authenticated_pending_onboarding") {
      void load();
    }
  }, [status, load]);

  return {
    ...state,
    reload: load,
  };
}