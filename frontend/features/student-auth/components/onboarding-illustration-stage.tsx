"use client";

import { motion, AnimatePresence } from "framer-motion";

type OnboardingIllustrationStageProps = {
  src: string;
  alt: string;
  stepKey: string;
  variant?: "framed" | "frameless";
};

export function OnboardingIllustrationStage({
  src,
  alt,
  stepKey,
  variant = "framed",
}: OnboardingIllustrationStageProps) {
  const isFrameless = variant === "frameless";

  return (
    <div
      className={
        isFrameless
          ? "relative px-2 py-2 sm:px-4 sm:py-4"
          : "onb-stage-surface relative overflow-hidden rounded-[2rem] border border-border/60 px-4 py-6 sm:px-6 sm:py-8"
      }
    >
      {!isFrameless ? (
        <div className="onb-stage-glow pointer-events-none absolute inset-x-0 top-0 mx-auto h-32 w-32 rounded-full blur-3xl" />
      ) : null}

      <AnimatePresence mode="wait">
        <motion.div
          key={stepKey}
          initial={{ opacity: 0, y: 18, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -14, scale: 0.98 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="onb-hero-wrap relative mx-auto flex w-full max-w-[320px] items-center justify-center sm:max-w-[380px] lg:max-w-[430px]"
        >
          <img
            src={src}
            alt={alt}
            className="h-auto w-full select-none object-contain"
            draggable={false}
          />
        </motion.div>
      </AnimatePresence>
    </div>
  );
}