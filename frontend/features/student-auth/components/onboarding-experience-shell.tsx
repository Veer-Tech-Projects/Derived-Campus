"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { ReactNode } from "react";

import { OnboardingProgressHeader } from "./onboarding-progress-header";
import { OnboardingIllustrationStage } from "./onboarding-illustration-stage";
import { OnboardingContentPanel } from "./onboarding-content-panel";

type OnboardingExperienceShellProps = {
  currentStep: number;
  totalSteps: number;
  title: string;
  subtitle: string;
  illustrationSrc: string;
  illustrationAlt: string;
  canGoBack: boolean;
  onBack: () => void;
  children: ReactNode;
};

export function OnboardingExperienceShell({
  currentStep,
  totalSteps,
  title,
  subtitle,
  illustrationSrc,
  illustrationAlt,
  canGoBack,
  onBack,
  children,
}: OnboardingExperienceShellProps) {
  return (
    <div className="onb-shell-bg min-h-screen text-foreground">
      <div className="onb-shell-overlay">
        <div className="onb-mobile-safe mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
          <div className="w-full max-w-5xl">
            <div className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:gap-8">
              <section className="order-1">
                <OnboardingProgressHeader
                  currentStep={currentStep}
                  totalSteps={totalSteps}
                  title={title}
                  subtitle={subtitle}
                  canGoBack={canGoBack}
                  onBack={onBack}
                />

                <div className="mt-5">
                  <OnboardingIllustrationStage
                    src={illustrationSrc}
                    alt={illustrationAlt}
                    stepKey={`illustration-${currentStep}`}
                    variant="frameless"
                  />
                </div>
              </section>

              <section className="order-2">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={`content-${currentStep}`}
                    initial={{ opacity: 0, y: 22 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -14 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                  >
                    <OnboardingContentPanel>{children}</OnboardingContentPanel>
                  </motion.div>
                </AnimatePresence>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}