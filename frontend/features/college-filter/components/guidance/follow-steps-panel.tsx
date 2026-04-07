"use client";

import { useEffect, useMemo, useRef } from "react";
import { Check } from "lucide-react";
import { FilterSchemaDTO, UUID } from "../../types/contracts";

type FollowStepsPanelProps = {
  selectedRootPathId: UUID | null;
  selectedEducationType: string | null;
  selectedFinalPathId: UUID | null;
  visibleFilters: FilterSchemaDTO[];
  shouldShowEducationTypeStep: boolean;
  shouldShowSelectionTypeStep: boolean;
  isFilterStepCompleted?: (filterKey: string) => boolean;
};

type GuidedStep = {
  key: string;
  label: string;
  meta: string;
  isCompleted: boolean;
};

export function FollowStepsPanel({
  selectedRootPathId,
  selectedEducationType,
  selectedFinalPathId,
  visibleFilters,
  shouldShowEducationTypeStep,
  shouldShowSelectionTypeStep,
  isFilterStepCompleted,
}: FollowStepsPanelProps) {
  const stepRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const steps = useMemo<GuidedStep[]>(() => {
    const builtSteps: GuidedStep[] = [
      {
        key: "root-path",
        label: "Select exam type",
        meta: "Required",
        isCompleted: Boolean(selectedRootPathId),
      },
    ];

    if (shouldShowEducationTypeStep) {
      builtSteps.push({
        key: "education-type",
        label: "Select education type",
        meta: "Required",
        isCompleted: Boolean(selectedEducationType),
      });
    }

    if (shouldShowSelectionTypeStep) {
      builtSteps.push({
        key: "selection-type",
        label: "Select selection type",
        meta: "Required",
        isCompleted: Boolean(selectedFinalPathId),
      });
    }

    if (selectedFinalPathId) {
      for (const filter of visibleFilters) {
        builtSteps.push({
          key: filter.filter_key,
          label: filter.filter_label,
          meta: filter.is_required ? "Required" : "Optional",
          isCompleted: isFilterStepCompleted?.(filter.filter_key) ?? false,
        });
      }
    }

    return builtSteps;
  }, [
    selectedRootPathId,
    selectedEducationType,
    selectedFinalPathId,
    shouldShowEducationTypeStep,
    shouldShowSelectionTypeStep,
    visibleFilters,
    isFilterStepCompleted,
  ]);

  const currentStepIndex = useMemo(() => {
    const firstIncompleteIndex = steps.findIndex((step) => !step.isCompleted);
    return firstIncompleteIndex === -1 ? Math.max(steps.length - 1, 0) : firstIncompleteIndex;
  }, [steps]);

  useEffect(() => {
    const currentStep = steps[currentStepIndex];
    if (!currentStep) return;

    const stepElement = stepRefs.current[currentStep.key];
    if (!stepElement) return;

    const scrollTimeout = setTimeout(() => {
      stepElement.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 50);

    return () => clearTimeout(scrollTimeout);
  }, [currentStepIndex, steps]);

  return (
    <div className="rounded-3xl border border-border bg-card p-6 shadow-sm xl:h-full xl:overflow-y-auto xl:cf-panel-scroll">
      
      {/* Constraint Wrapper: Centers content and enforces a tight, enterprise width */}
      <div className="mx-auto flex w-full max-w-[420px] flex-col py-4 xl:py-6">
        
        {/* Enterprise Progress Header */}
        <div className="mb-10 space-y-3 border-b border-border/60 pb-6 text-center sm:text-left">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
            <Check className="h-3.5 w-3.5" strokeWidth={3} />
            <span>Setup Progress</span>
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Complete selection flow
          </h2>
          <p className="text-sm leading-6 text-muted-foreground">
            Please provide the required details on the left. Your results will automatically generate once complete.
          </p>
        </div>

        {/* The Unified Tracker Container with Strict Gap Enforcement */}
        <div className="relative flex flex-col gap-5">
          {steps.map((step, index) => (
            <div
              key={step.key}
              ref={(node) => {
                stepRefs.current[step.key] = node;
              }}
            >
              <StepRow
                label={step.label}
                meta={step.meta}
                isCompleted={step.isCompleted}
                isCurrent={index === currentStepIndex}
                isLast={index === steps.length - 1}
              />
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

type StepRowProps = {
  label: string;
  meta: string;
  isCompleted: boolean;
  isCurrent: boolean;
  isLast: boolean;
};

function StepRow({ label, meta, isCompleted, isCurrent, isLast }: StepRowProps) {
  const isPending = !isCompleted && !isCurrent;

  const nodeBase = "relative z-10 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300";

  let nodeStyle = "";
  if (isCompleted) {
    nodeStyle = "border-emerald-500 bg-emerald-500 text-white shadow-sm";
  } else if (isCurrent) {
    nodeStyle = "border-primary bg-background ring-4 ring-primary/20 shadow-sm";
  } else {
    nodeStyle = "border-border/80 bg-background";
  }

  // Enterprise SaaS Plate Styling
  let plateStyle = "";
  if (isCompleted) {
    plateStyle = "border-emerald-500/20 bg-emerald-500/5"; // Restored soft green plate
  } else if (isCurrent) {
    plateStyle = "border-primary/30 bg-primary/5 ring-1 ring-primary/20 shadow-sm";
  } else {
    plateStyle = "border-border/60 border-dashed bg-transparent opacity-60 transition-opacity hover:opacity-100";
  }

  return (
    <div className="group relative flex w-full items-start gap-4 sm:gap-5">
      
      {/* Precision Mathematical Rail (Bridges the exact gap) */}
      {!isLast && (
        <div
          className={[
            "absolute left-[15px] top-[36px] w-[2px] h-[calc(100%-12px)] transition-colors duration-500",
            isCompleted ? "bg-emerald-400" : "bg-border/60"
          ].join(" ")}
        />
      )}

      {/* Node Container */}
      <div className={`${nodeBase} ${nodeStyle}`}>
        {isCompleted && <Check className="h-4 w-4" strokeWidth={3} />}
        {isCurrent && <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />}
        {isPending && <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />}
      </div>

      {/* Interactive Content Plate */}
      <div className={`flex flex-1 flex-col justify-center rounded-2xl border px-4 py-3.5 transition-all duration-300 ${plateStyle}`}>
        <div
          className={[
            "text-sm font-semibold leading-tight",
            isCurrent ? "text-primary" : "text-foreground"
          ].join(" ")}
        >
          {label}
        </div>
        {/* Strictly muted text as requested, with premium wide-tracking */}
        <div className="mt-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          {meta}
        </div>
      </div>
    </div>
  );
}