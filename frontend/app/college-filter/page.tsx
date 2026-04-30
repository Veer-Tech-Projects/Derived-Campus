"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { CollegeFilterPageShell } from "@/features/college-filter/components/page/college-filter-page-shell";
import {
  ResultsWorkspaceSkeleton,
  SelectionPanelSkeleton,
} from "@/features/college-filter/components/shared/skeletons";
import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";

function CollegeFilterGateLoading() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col gap-3 px-2.5 py-2.5 md:px-4 lg:px-5">
      <div className="grid gap-3 xl:h-[calc(100vh-1.25rem)] xl:grid-cols-[320px_minmax(0,1fr)]">
        <section className="min-h-0 rounded-3xl border border-border bg-card shadow-sm xl:flex xl:flex-col xl:overflow-hidden">
          <div className="min-h-0 px-4 py-3 xl:flex-1 xl:overflow-y-auto xl:cf-panel-scroll">
            <SelectionPanelSkeleton />
          </div>
        </section>

        <section className="min-h-0 rounded-3xl border border-border bg-card shadow-sm xl:flex xl:flex-col xl:overflow-hidden">
          <div className="min-h-0 px-4 py-3 xl:flex-1 xl:overflow-hidden">
            <div className="min-h-0 xl:h-full xl:overflow-y-auto xl:cf-panel-scroll">
              <ResultsWorkspaceSkeleton cardCount={2} />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function CollegeFilterPage() {
  const router = useRouter();
  const { status, initialized, accessToken } = useStudentAuth();

  useEffect(() => {
    if (!initialized) {
      return;
    }

    if (status === "unauthenticated") {
      router.replace(studentAuthRouteConfig.loginPath);
      return;
    }

    if (status === "authenticated_pending_onboarding") {
      router.replace(studentAuthRouteConfig.onboardingPath);
      return;
    }
  }, [initialized, router, status]);

  const isHydrating =
    !initialized || status === "unknown" || status === "refreshing";

  if (isHydrating) {
    return <CollegeFilterGateLoading />;
  }

  if (
    status === "unauthenticated" ||
    status === "authenticated_pending_onboarding"
  ) {
    return null;
  }

  if (status !== "authenticated_completed") {
    return <CollegeFilterGateLoading />;
  }

  return <CollegeFilterPageShell accessToken={accessToken} />;
}