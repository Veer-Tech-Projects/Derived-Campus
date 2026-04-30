"use client";

import type { PointerEvent } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";

import type { BillingPackageCardViewModel } from "../../types/student-billing-view-models";
import { useStudentBillingPackageCarousel } from "../../hooks/use-student-billing-package-carousel";
import { StudentBillingPackageCard } from "./student-billing-package-card";

type StudentBillingPackageCarouselProps = {
  packages: BillingPackageCardViewModel[];
  activePackageCode?: string | null;
  isBusy?: boolean;
  onBuyNow?: (packageCode: string) => void;
};

const CARD_SNAP_TRANSITION =
  "transform 340ms cubic-bezier(0.22, 1, 0.36, 1), opacity 340ms cubic-bezier(0.22, 1, 0.36, 1)";

const ACTIVE_WIDTH_PERCENT = 80;
const SIDE_WIDTH_PERCENT = 80;
const SIDE_PEEK_OFFSET_PX = 88;
const ACTIVE_DRAG_MULTIPLIER = 1;
const SIDE_DRAG_MULTIPLIER = 0.22;

function buildActiveTransform(dragOffsetX: number): string {
  return `translate3d(${dragOffsetX * ACTIVE_DRAG_MULTIPLIER}px, 0, 0)`;
}

function buildSideTransform(
  side: "left" | "right",
  dragOffsetX: number,
): string {
  const direction = side === "left" ? -1 : 1;

  return `translate3d(${direction * SIDE_PEEK_OFFSET_PX + dragOffsetX * SIDE_DRAG_MULTIPLIER}px, 0, 0)`;
}

export function StudentBillingPackageCarousel({
  packages,
  activePackageCode = null,
  isBusy = false,
  onBuyNow,
}: StudentBillingPackageCarouselProps) {
  const carousel = useStudentBillingPackageCarousel({
    itemCount: packages.length,
    initialIndex: 0,
  });

  if (packages.length === 0) {
    return null;
  }

  if (packages.length === 1) {
    const onlyPackage = packages[0];

    return (
      <div className="lg:hidden">
        <div className="mx-auto w-[92%]">
          <StudentBillingPackageCard
            packageViewModel={onlyPackage}
            isHighlighted
            isBusy={isBusy && activePackageCode === onlyPackage.packageCode}
            isActivePurchase={activePackageCode === onlyPackage.packageCode}
            onBuyNow={onBuyNow}
          />
        </div>
      </div>
    );
  }

  const activePackage = packages[carousel.activeIndex];
  const previousPackage = packages[carousel.previousIndex];
  const nextPackage = packages[carousel.nextIndex];

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (packages.length <= 1) {
      return;
    }

    event.currentTarget.setPointerCapture(event.pointerId);
    carousel.handlePointerDown(event.clientX);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    carousel.handlePointerMove(event.clientX);
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    carousel.handlePointerUp(event.clientX);
  };

  const handlePointerCancel = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    carousel.handlePointerCancel();
  };

  const transitionStyle = carousel.isDragging ? "none" : CARD_SNAP_TRANSITION;

  return (
    <div className="lg:hidden">
      <div
        className="relative overflow-hidden rounded-[2rem]"
        role="region"
        aria-roledescription="carousel"
        aria-label="Student billing subscriptions"
        tabIndex={0}
        onKeyDown={carousel.handleKeyDown}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        style={{ touchAction: "pan-y" }}
      >
        <p className="sr-only" aria-live="polite">
          {carousel.ariaAnnouncement}
        </p>

        <div className="relative h-[38rem]">
          <div
            className="pointer-events-none absolute left-1/2 top-0 z-10 -translate-x-1/2"
            style={{
              width: `${SIDE_WIDTH_PERCENT}%`,
              transform: buildSideTransform("left", carousel.dragOffsetX),
              opacity: 0.5,
              transition: transitionStyle,
              willChange: "transform, opacity",
            }}
          >
            <StudentBillingPackageCard
              packageViewModel={previousPackage}
              isBusy={false}
            />
          </div>

          <div
            className="absolute left-1/2 top-0 z-20 -translate-x-1/2"
            style={{
              width: `${ACTIVE_WIDTH_PERCENT}%`,
              transform: buildActiveTransform(carousel.dragOffsetX),
              opacity: 1,
              transition: transitionStyle,
              willChange: "transform, opacity",
            }}
          >
            <StudentBillingPackageCard
              packageViewModel={activePackage}
              isHighlighted
              isBusy={isBusy && activePackageCode === activePackage.packageCode}
              isActivePurchase={activePackageCode === activePackage.packageCode}
              onBuyNow={onBuyNow}
            />
          </div>

          <div
            className="pointer-events-none absolute left-1/2 top-0 z-10 -translate-x-1/2"
            style={{
              width: `${SIDE_WIDTH_PERCENT}%`,
              transform: buildSideTransform("right", carousel.dragOffsetX),
              opacity: 0.5,
              transition: transitionStyle,
              willChange: "transform, opacity",
            }}
          >
            <StudentBillingPackageCard
              packageViewModel={nextPackage}
              isBusy={false}
            />
          </div>
        </div>

        <div className="mt-2 flex items-center justify-center gap-2">
          {packages.map((item, index) => (
            <button
              key={item.packageId}
              type="button"
              onClick={() => carousel.goToIndex(index)}
              className={[
                "h-2.5 rounded-full transition-all",
                carousel.activeIndex === index
                  ? "w-6 bg-primary"
                  : "w-2.5 bg-border",
              ].join(" ")}
              aria-label={`Show ${item.displayName}`}
              aria-pressed={carousel.activeIndex === index}
            />
          ))}
        </div>

        <div className="mt-2 flex items-center justify-center gap-2.5 text-sm font-medium text-muted-foreground">
          <ArrowLeft className="h-4 w-4" />
          <span>Swipe to explore more plans</span>
          <ArrowRight className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}