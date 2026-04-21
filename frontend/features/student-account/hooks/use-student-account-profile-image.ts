"use client";

import { useMemo } from "react";

import { useProfileImageFlow } from "@/features/student-auth/hooks/use-profile-image-flow";
import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";

export function useStudentAccountProfileImage() {
  const { accessToken, profile, refreshSession } = useStudentAuth();

  const canonicalProfileImageUrl = profile?.profile_image_url ?? null;
  const canonicalHasUploadedAvatar = Boolean(profile?.profile_image_storage_key);

  const imageFlow = useProfileImageFlow({
    accessToken,
    currentProfileImageUrl: canonicalProfileImageUrl,
    canEditUploadedAvatar: canonicalHasUploadedAvatar,
    refreshSession,
    reloadOnboardingState: refreshSession,
  });

  return useMemo(
    () => ({
      currentProfileImageUrl: imageFlow.effectiveProfileImageUrl,
      canEditUploadedAvatar: imageFlow.effectiveCanEditUploadedAvatar,
      fileInputRef: imageFlow.fileInputRef,
      uploadState: imageFlow.uploadState,
      imageDraft: imageFlow.imageDraft,
      previewImageUrl: imageFlow.previewImageUrl,
      isPreviewModalOpen: imageFlow.isPreviewModalOpen,
      isCropModalOpen: imageFlow.isCropModalOpen,
      crop: imageFlow.crop,
      zoom: imageFlow.zoom,
      cropPixels: imageFlow.cropPixels,
      handleImageFileSelection: imageFlow.handleImageFileSelection,
      handleEditCurrentImage: imageFlow.handleEditCurrentImage,
      handleSaveCrop: imageFlow.handleSaveCrop,
      handleUnsaveCrop: imageFlow.handleUnsaveCrop,
      handleApplyUpload: imageFlow.handleApplyUpload,
      openCropModal: imageFlow.openCropModal,
      closePreviewModal: imageFlow.closePreviewModal,
      setCrop: imageFlow.setCrop,
      setZoom: imageFlow.setZoom,
      setCropPixels: imageFlow.setCropPixels,
    }),
    [
      imageFlow.effectiveProfileImageUrl,
      imageFlow.effectiveCanEditUploadedAvatar,
      imageFlow.fileInputRef,
      imageFlow.uploadState,
      imageFlow.imageDraft,
      imageFlow.previewImageUrl,
      imageFlow.isPreviewModalOpen,
      imageFlow.isCropModalOpen,
      imageFlow.crop,
      imageFlow.zoom,
      imageFlow.cropPixels,
      imageFlow.handleImageFileSelection,
      imageFlow.handleEditCurrentImage,
      imageFlow.handleSaveCrop,
      imageFlow.handleUnsaveCrop,
      imageFlow.handleApplyUpload,
      imageFlow.openCropModal,
      imageFlow.closePreviewModal,
      imageFlow.setCrop,
      imageFlow.setZoom,
      imageFlow.setCropPixels,
    ],
  );
}