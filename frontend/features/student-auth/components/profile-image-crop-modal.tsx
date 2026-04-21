"use client";

import Cropper from "react-easy-crop";
import type { Area } from "react-easy-crop";
import { Crop } from "lucide-react";

type Props = {
  open: boolean;
  imageSrc: string | null;
  crop: { x: number; y: number };
  zoom: number;
  onCropChange: (crop: { x: number; y: number }) => void;
  onZoomChange: (zoom: number) => void;
  onCropComplete: (croppedArea: Area, croppedAreaPixels: Area) => void;
  onSaveCrop: () => void;
  onUnsave: () => void;
};

export function ProfileImageCropModal({
  open,
  imageSrc,
  crop,
  zoom,
  onCropChange,
  onZoomChange,
  onCropComplete,
  onSaveCrop,
  onUnsave,
}: Props) {
  if (!open || !imageSrc) return null;

  return (
    <div className="fixed inset-0 z-[60] bg-background/85 backdrop-blur-sm">
      <div className="flex min-h-screen items-center justify-center p-3 sm:p-4 lg:p-6">
        <div className="flex h-[calc(100vh-1.5rem)] w-full max-w-6xl flex-col overflow-hidden rounded-[2rem] border border-border bg-card shadow-2xl sm:h-[calc(100vh-2rem)] lg:h-[calc(100vh-3rem)]">
          <div className="shrink-0 border-b border-border px-5 py-4 sm:px-6">
            <div className="flex items-start gap-3">
              <div className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <Crop className="h-4 w-4" />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-foreground sm:text-xl">
                  Adjust crop
                </h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Drag the image and use zoom to refine your square avatar crop.
                </p>
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6 sm:py-6">
            <div className="space-y-6 pb-32 sm:pb-36">
              <div className="relative h-[320px] overflow-hidden rounded-[1.75rem] border border-border bg-[linear-gradient(45deg,#f2f2f2_25%,transparent_25%),linear-gradient(-45deg,#f2f2f2_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#f2f2f2_75%),linear-gradient(-45deg,transparent_75%,#f2f2f2_75%)] bg-[length:24px_24px] bg-[position:0_0,0_12px,12px_-12px,-12px_0px] sm:h-[420px] lg:h-[500px] dark:bg-[linear-gradient(45deg,#1f1f1f_25%,transparent_25%),linear-gradient(-45deg,#1f1f1f_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#1f1f1f_75%),linear-gradient(-45deg,transparent_75%,#1f1f1f_75%)]">
                <Cropper
                  image={imageSrc}
                  crop={crop}
                  zoom={zoom}
                  aspect={1}
                  cropShape="rect"
                  showGrid
                  onCropChange={onCropChange}
                  onZoomChange={onZoomChange}
                  onCropComplete={onCropComplete}
                />
              </div>
            </div>
          </div>

          <div className="shrink-0 border-t border-border bg-card/95 px-4 py-4 backdrop-blur-sm sm:px-6">
            <div className="mx-auto max-w-5xl space-y-4">
              <div className="rounded-[1.25rem] border border-border/70 bg-secondary/20 p-4 sm:p-5">
                <div className="flex items-center justify-between gap-4 text-xs font-medium text-muted-foreground">
                  <span>Zoom</span>
                  <span>{zoom.toFixed(1)}x</span>
                </div>

                <input
                  type="range"
                  min={1}
                  max={3}
                  step={0.1}
                  value={zoom}
                  onChange={(event) => onZoomChange(Number(event.target.value))}
                  className="mt-4 w-full"
                />
              </div>

              <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                <button
                  type="button"
                  onClick={onUnsave}
                  className="flex h-12 items-center justify-center rounded-2xl border border-border/70 bg-background px-5 text-sm font-semibold text-foreground transition hover:bg-accent hover:text-accent-foreground"
                >
                  Unsave
                </button>

                <button
                  type="button"
                  onClick={onSaveCrop}
                  className="flex h-12 min-w-[180px] items-center justify-center rounded-2xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-95"
                >
                  Save crop
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}