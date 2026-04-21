"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles } from "lucide-react";

import {
  buildStudentProviderLoginUrl,
  getStudentAuthProviders,
} from "@/features/student-auth/api/student-auth-api";
import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import type { StudentAuthProviderDTO } from "@/features/student-auth/types/student-auth-contracts";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";

type ProvidersState = {
  loading: boolean;
  items: StudentAuthProviderDTO[];
  errorMessage: string | null;
};

const initialProvidersState: ProvidersState = {
  loading: true,
  items: [],
  errorMessage: null,
};

const providerVisualOrder: Record<string, number> = {
  GOOGLE: 1,
  FACEBOOK: 2,
};

function getProviderIconSrc(provider: StudentAuthProviderDTO["provider"]) {
  switch (provider) {
    case "GOOGLE":
      return "/brands/student-auth/google.svg";
    case "FACEBOOK":
      return "/brands/student-auth/facebook.svg";
    default:
      return null;
  }
}

function getProviderButtonClasses(provider: StudentAuthProviderDTO["provider"]) {
  switch (provider) {
    case "GOOGLE":
      return {
        outer:
          "border-border/80 bg-white text-[#1f1f1f] shadow-[0_16px_40px_rgba(15,23,42,0.08)] hover:bg-[#faf7ff] dark:border-white/10 dark:bg-white dark:text-[#1f1f1f]",
        iconWrap: "bg-white",
        arrow: "text-[#1f1f1f]/70",
      };
    case "FACEBOOK":
      return {
        outer:
          "border-[#4d83eb] bg-[#4d83eb] text-white shadow-[0_18px_44px_rgba(77,131,235,0.24)] hover:bg-[#3f76db]",
        iconWrap: "bg-white/14",
        arrow: "text-white/90",
      };
    default:
      return {
        outer:
          "border-border/80 bg-card text-foreground hover:bg-accent hover:text-accent-foreground",
        iconWrap: "bg-background",
        arrow: "text-foreground/70",
      };
  }
}

export default function StudentLoginPage() {
  const router = useRouter();
  const { status, initialized } = useStudentAuth();

  const [providersState, setProvidersState] =
    useState<ProvidersState>(initialProvidersState);

  useEffect(() => {
    if (!initialized) {
      return;
    }

    if (status === "authenticated_pending_onboarding") {
      router.replace(studentAuthRouteConfig.onboardingPath);
      return;
    }

    if (status === "authenticated_completed") {
      router.replace(studentAuthRouteConfig.postLoginPath);
      return;
    }
  }, [initialized, router, status]);

  useEffect(() => {
    if (!initialized) {
      return;
    }

    if (status !== "unauthenticated") {
      return;
    }

    let cancelled = false;

    async function loadProviders() {
      setProvidersState({
        loading: true,
        items: [],
        errorMessage: null,
      });

      try {
        const response = await getStudentAuthProviders();

        if (cancelled) {
          return;
        }

        setProvidersState({
          loading: false,
          items: response.filter((provider) => provider.enabled),
          errorMessage: null,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Failed to load login providers.";

        setProvidersState({
          loading: false,
          items: [],
          errorMessage: message,
        });
      }
    }

    void loadProviders();

    return () => {
      cancelled = true;
    };
  }, [initialized, status]);

  const orderedProviders = useMemo(() => {
    return [...providersState.items].sort((left, right) => {
      const leftOrder = providerVisualOrder[left.provider] ?? 999;
      const rightOrder = providerVisualOrder[right.provider] ?? 999;
      return leftOrder - rightOrder;
    });
  }, [providersState.items]);

  const isHydrating =
    !initialized || status === "unknown" || status === "refreshing";

  if (isHydrating) {
    return (
      <div className="onb-shell-bg onb-shell-overlay onb-mobile-safe flex min-h-screen items-center justify-center px-4 text-foreground">
        <div className="onb-panel w-full max-w-md rounded-[2rem] border border-border/60 bg-card p-6 shadow-[0_20px_50px_rgba(0,0,0,0.08)] sm:p-8">
          <div className="space-y-3">
            <div className="h-5 w-28 animate-pulse rounded-full bg-muted" />
            <div className="h-10 w-3/4 animate-pulse rounded-2xl bg-muted" />
            <div className="h-4 w-full animate-pulse rounded-xl bg-muted" />
            <div className="h-16 w-full animate-pulse rounded-[1.75rem] bg-muted" />
            <div className="h-16 w-full animate-pulse rounded-[1.75rem] bg-muted" />
          </div>
        </div>
      </div>
    );
  }

  if (
    status === "authenticated_pending_onboarding" ||
    status === "authenticated_completed"
  ) {
    return null;
  }

  return (
    <div className="onb-shell-bg text-foreground">
      <div className="onb-shell-overlay onb-mobile-safe">
        <div className="mx-auto flex min-h-screen w-full max-w-7xl items-center px-4 py-5 sm:px-6 lg:px-8">
          <div className="grid w-full items-center gap-8 lg:grid-cols-[minmax(0,1.04fr)_minmax(380px,470px)] lg:gap-10">
            <section className="order-1">
              <div className="mx-auto max-w-2xl space-y-7 lg:mx-0">
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground shadow-sm">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  Derived Campus
                </div>

                <div className="space-y-3">
                  <h1 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl lg:text-[3.4rem] lg:leading-[1.02]">
                    College counselling, made simpler
                  </h1>
                  <p className="max-w-lg text-sm leading-7 text-muted-foreground sm:text-base">
                    Continue with Derived Campus to explore better-fit colleges
                    with your progress and preferences saved.
                  </p>
                </div>

                <div className="pt-2">
                  <div className="relative mx-auto flex w-full max-w-[300px] items-center justify-center sm:max-w-[360px] lg:mx-0 lg:max-w-[440px]">
                    <img
                      src="/illustrations/student-auth/login-illustration.svg"
                      alt="Students welcoming a learner to the platform"
                      className="h-auto w-full select-none object-contain"
                      draggable={false}
                    />
                  </div>
                </div>
              </div>
            </section>

            <section className="order-2">
              <div className="mx-auto w-full max-w-md">
                <div className="onb-panel rounded-[2.2rem] border border-border/60 bg-card px-5 py-6 shadow-[0_30px_80px_rgba(0,0,0,0.11)] sm:px-7 sm:py-7">
                  <div className="space-y-2.5">
                    <div className="inline-flex items-center rounded-full border border-border/70 bg-secondary/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                      Student login
                    </div>

                    <div className="space-y-2">
                      <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-[1.9rem]">
                        Sign in and continue
                      </h2>
                      <p className="text-sm leading-7 text-muted-foreground">
                        Choose your secure provider to start or resume your
                        student onboarding on Derived Campus.
                      </p>
                    </div>
                  </div>

                  <div className="mt-7 space-y-4">
                    {providersState.loading ? (
                      <div className="space-y-3">
                        <div className="h-16 w-full animate-pulse rounded-[1.75rem] bg-muted" />
                        <div className="h-16 w-full animate-pulse rounded-[1.75rem] bg-muted" />
                      </div>
                    ) : providersState.errorMessage ? (
                      <div className="rounded-[1.5rem] border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                        {providersState.errorMessage}
                      </div>
                    ) : orderedProviders.length === 0 ? (
                      <div className="rounded-[1.5rem] border border-border/70 bg-background/80 p-4 text-sm text-muted-foreground">
                        No student login providers are enabled right now.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {orderedProviders.map((provider) => {
                          const iconSrc = getProviderIconSrc(provider.provider);
                          const visual = getProviderButtonClasses(provider.provider);

                          return (
                            <button
                              key={provider.provider}
                              type="button"
                              onClick={() => {
                                window.location.assign(
                                  buildStudentProviderLoginUrl(provider.provider),
                                );
                              }}
                              className={[
                                "group flex h-[4.25rem] w-full cursor-pointer items-center justify-between rounded-[1.9rem] border px-5 text-left transition-all duration-200 hover:-translate-y-[1px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                                visual.outer,
                              ].join(" ")}
                            >
                              <span className="flex min-w-0 items-center gap-4">
                                <span
                                  className={[
                                    "flex h-11 w-11 shrink-0 items-center justify-center rounded-[1.05rem]",
                                    visual.iconWrap,
                                  ].join(" ")}
                                >
                                  {iconSrc ? (
                                    <img
                                      src={iconSrc}
                                      alt={`${provider.display_label} logo`}
                                      className="h-6 w-6 object-contain"
                                      draggable={false}
                                    />
                                  ) : null}
                                </span>

                                <span className="truncate text-[1.02rem] font-semibold sm:text-lg">
                                  {`Continue with ${provider.display_label}`}
                                </span>
                              </span>

                              <ArrowRight
                                className={[
                                  "h-5 w-5 shrink-0 transition-transform duration-200 group-hover:translate-x-0.5",
                                  visual.arrow,
                                ].join(" ")}
                              />
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  <div className="mt-6 rounded-[1.5rem] border border-border/60 bg-background/75 p-4">
                    <p className="text-xs leading-6 text-muted-foreground">
                      Secure provider sign-in with saved progress, synced onboarding,
                      and personalized college discovery.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}