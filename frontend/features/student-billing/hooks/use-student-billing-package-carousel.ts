"use client";

import { useCallback, useMemo, useState } from "react";

type UseStudentBillingPackageCarouselOptions = {
  itemCount: number;
  initialIndex?: number;
};

type UseStudentBillingPackageCarouselResult = {
  activeIndex: number;
  previousIndex: number;
  nextIndex: number;
  dragOffsetX: number;
  isDragging: boolean;
  goNext: () => void;
  goPrevious: () => void;
  goToIndex: (index: number) => void;
  handleKeyDown: (event: React.KeyboardEvent<HTMLElement>) => void;
  handlePointerDown: (clientX: number) => void;
  handlePointerMove: (clientX: number) => void;
  handlePointerUp: (clientX: number) => void;
  handlePointerCancel: () => void;
  ariaAnnouncement: string;
};

const SWIPE_THRESHOLD_PX = 56;
const MAX_DRAG_OFFSET_PX = 140;
const DRAG_FRICTION = 0.9;

function normalizeIndex(index: number, itemCount: number): number {
  if (itemCount <= 0) {
    return 0;
  }

  return ((index % itemCount) + itemCount) % itemCount;
}

function clampDragOffset(rawDelta: number): number {
  const adjusted = rawDelta * DRAG_FRICTION;
  return Math.max(-MAX_DRAG_OFFSET_PX, Math.min(MAX_DRAG_OFFSET_PX, adjusted));
}

export function useStudentBillingPackageCarousel({
  itemCount,
  initialIndex = 0,
}: UseStudentBillingPackageCarouselOptions): UseStudentBillingPackageCarouselResult {
  const safeItemCount = Math.max(itemCount, 1);

  const [activeIndex, setActiveIndex] = useState(
    normalizeIndex(initialIndex, safeItemCount),
  );
  const [dragStartX, setDragStartX] = useState<number | null>(null);
  const [dragOffsetX, setDragOffsetX] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  const previousIndex = useMemo(
    () => normalizeIndex(activeIndex - 1, safeItemCount),
    [activeIndex, safeItemCount],
  );

  const nextIndex = useMemo(
    () => normalizeIndex(activeIndex + 1, safeItemCount),
    [activeIndex, safeItemCount],
  );

  const resetDragState = useCallback(() => {
    setDragStartX(null);
    setDragOffsetX(0);
    setIsDragging(false);
  }, []);

  const goToIndex = useCallback(
    (index: number) => {
      setActiveIndex(normalizeIndex(index, safeItemCount));
      setDragOffsetX(0);
      setIsDragging(false);
      setDragStartX(null);
    },
    [safeItemCount],
  );

  const goNext = useCallback(() => {
    if (itemCount <= 1) {
      resetDragState();
      return;
    }

    setActiveIndex((current) => normalizeIndex(current + 1, safeItemCount));
    resetDragState();
  }, [itemCount, resetDragState, safeItemCount]);

  const goPrevious = useCallback(() => {
    if (itemCount <= 1) {
      resetDragState();
      return;
    }

    setActiveIndex((current) => normalizeIndex(current - 1, safeItemCount));
    resetDragState();
  }, [itemCount, resetDragState, safeItemCount]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrevious();
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    },
    [goNext, goPrevious],
  );

  const handlePointerDown = useCallback(
    (clientX: number) => {
      if (itemCount <= 1) {
        return;
      }

      setDragStartX(clientX);
      setDragOffsetX(0);
      setIsDragging(true);
    },
    [itemCount],
  );

  const handlePointerMove = useCallback(
    (clientX: number) => {
      if (!isDragging || dragStartX === null) {
        return;
      }

      const rawDelta = clientX - dragStartX;
      setDragOffsetX(clampDragOffset(rawDelta));
    },
    [dragStartX, isDragging],
  );

  const handlePointerUp = useCallback(
    (clientX: number) => {
      if (!isDragging || dragStartX === null) {
        resetDragState();
        return;
      }

      const rawDelta = clientX - dragStartX;
      const finalDelta = clampDragOffset(rawDelta);

      if (Math.abs(finalDelta) < SWIPE_THRESHOLD_PX) {
        resetDragState();
        return;
      }

      if (finalDelta < 0) {
        goNext();
        return;
      }

      goPrevious();
    },
    [dragStartX, goNext, goPrevious, isDragging, resetDragState],
  );

  const handlePointerCancel = useCallback(() => {
    resetDragState();
  }, [resetDragState]);

  const ariaAnnouncement = useMemo(() => {
    if (itemCount <= 0) {
      return "No billing packages available.";
    }

    return `Showing package ${activeIndex + 1} of ${itemCount}`;
  }, [activeIndex, itemCount]);

  return {
    activeIndex,
    previousIndex,
    nextIndex,
    dragOffsetX,
    isDragging,
    goNext,
    goPrevious,
    goToIndex,
    handleKeyDown,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handlePointerCancel,
    ariaAnnouncement,
  };
}