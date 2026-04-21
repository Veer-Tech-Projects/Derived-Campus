"use client";

import type { Area } from "react-easy-crop";

import { ProfileImageCropModal } from "@/features/student-auth/components/profile-image-crop-modal";
import { ProfileImagePreviewModal } from "@/features/student-auth/components/profile-image-preview-modal";

type StudentAccountProfileImageEditorProps = {
  isPreviewModalOpen: boolean;
  previewImageUrl: string | null;
  hasUnsavedCrop: boolean;
  uploading: boolean;
  errorMessage: string | null;
  onOpenCrop: () => void;
  onApply: () => void | Promise<void>;
  onCancel: () => void;

  isCropModalOpen: boolean;
  cropImageSrc: string | null;
  crop: { x: number; y: number };
  zoom: number;
  onCropChange: (crop: { x: number; y: number }) => void;
  onZoomChange: (zoom: number) => void;
  onCropComplete: (croppedArea: Area, croppedAreaPixels: Area) => void;
  onSaveCrop: () => void | Promise<void>;
  onUnsaveCrop: () => void;
};

export function StudentAccountProfileImageEditor({
  isPreviewModalOpen,
  previewImageUrl,
  hasUnsavedCrop,
  uploading,
  errorMessage,
  onOpenCrop,
  onApply,
  onCancel,
  isCropModalOpen,
  cropImageSrc,
  crop,
  zoom,
  onCropChange,
  onZoomChange,
  onCropComplete,
  onSaveCrop,
  onUnsaveCrop,
}: StudentAccountProfileImageEditorProps) {
  return (
    <>
      <ProfileImagePreviewModal
        open={isPreviewModalOpen}
        previewImageUrl={previewImageUrl}
        hasUnsavedCrop={hasUnsavedCrop}
        uploading={uploading}
        errorMessage={errorMessage}
        onCrop={onOpenCrop}
        onApply={() => void onApply()}
        onCancel={onCancel}
      />

      <ProfileImageCropModal
        open={isCropModalOpen}
        imageSrc={cropImageSrc}
        crop={crop}
        zoom={zoom}
        onCropChange={onCropChange}
        onZoomChange={onZoomChange}
        onCropComplete={onCropComplete}
        onSaveCrop={() => void onSaveCrop()}
        onUnsave={onUnsaveCrop}
      />
    </>
  );
}