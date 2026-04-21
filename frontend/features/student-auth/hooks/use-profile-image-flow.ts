"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Area } from "react-easy-crop";

import { uploadStudentProfileImage } from "../api/student-auth-api";
import { studentAuthUiConfig } from "../config/student-auth-ui-config";
import type {
  ImageDraftState,
  ProfileImageUploadState,
} from "../onboarding/onboarding-types";
import { createCroppedImageFile } from "../utils/crop-image";

type UseProfileImageFlowArgs = {
  accessToken: string | null;
  currentProfileImageUrl: string | null;
  canEditUploadedAvatar: boolean;
  refreshSession: () => Promise<void>;
  reloadOnboardingState: () => Promise<void>;
};

type OptimisticUploadState = {
  profileImageUrl: string;
  profileImageStorageKey: string;
} | null;

function isAllowedMimeType(type: string): boolean {
  return studentAuthUiConfig.profileImageAllowedMimeTypes.includes(
    type.trim().toLowerCase(),
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(0)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function useProfileImageFlow({
  accessToken,
  currentProfileImageUrl,
  canEditUploadedAvatar,
  refreshSession,
  reloadOnboardingState,
}: UseProfileImageFlowArgs) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [uploadState, setUploadState] = useState<ProfileImageUploadState>({
    uploading: false,
    errorMessage: null,
  });

  const [imageDraft, setImageDraft] = useState<ImageDraftState | null>(null);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [isCropModalOpen, setIsCropModalOpen] = useState(false);
  const [optimisticUpload, setOptimisticUpload] =
    useState<OptimisticUploadState>(null);

  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [cropPixels, setCropPixels] = useState<Area | null>(null);

  const activeUrlsRef = useRef<{ original: string | null; working: string | null }>({
    original: null,
    working: null,
  });

  useEffect(() => {
    activeUrlsRef.current = {
      original: imageDraft?.originalPreviewUrl ?? null,
      working: imageDraft?.workingPreviewUrl ?? null,
    };
  }, [imageDraft]);

  useEffect(() => {
    return () => {
      const { original, working } = activeUrlsRef.current;

      if (original) {
        URL.revokeObjectURL(original);
      }

      if (working && working !== original) {
        URL.revokeObjectURL(working);
      }
    };
  }, []);

    useEffect(() => {
    if (!optimisticUpload) {
      return;
    }

    if (
      currentProfileImageUrl &&
      currentProfileImageUrl === optimisticUpload.profileImageUrl
    ) {
      setOptimisticUpload(null);
    }
  }, [currentProfileImageUrl, optimisticUpload]);

  const previewImageUrl = useMemo(
    () => imageDraft?.workingPreviewUrl ?? null,
    [imageDraft],
  );

  const effectiveProfileImageUrl =
    optimisticUpload?.profileImageUrl ?? currentProfileImageUrl;

  const effectiveCanEditUploadedAvatar =
    Boolean(optimisticUpload?.profileImageStorageKey) || canEditUploadedAvatar;

  function resetFileInput() {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function clearDraft() {
    setImageDraft((prev) => {
      if (!prev) return null;

      URL.revokeObjectURL(prev.originalPreviewUrl);
      if (prev.workingPreviewUrl !== prev.originalPreviewUrl) {
        URL.revokeObjectURL(prev.workingPreviewUrl);
      }

      activeUrlsRef.current = {
        original: null,
        working: null,
      };

      return null;
    });
  }

  function closePreviewModal() {
    setIsPreviewModalOpen(false);
    setIsCropModalOpen(false);
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setCropPixels(null);
    clearDraft();
    resetFileInput();
    setUploadState({
      uploading: false,
      errorMessage: null,
    });
  }

  function openCropModal() {
    if (!imageDraft) return;

    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setCropPixels(null);
    setIsCropModalOpen(true);
  }

  function handleImageFileSelection(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    if (!isAllowedMimeType(selectedFile.type)) {
      setUploadState({
        uploading: false,
        errorMessage: "Unsupported image type. Allowed types: jpeg, png, webp.",
      });
      resetFileInput();
      return;
    }

    if (selectedFile.size > studentAuthUiConfig.profileImageMaxBytes) {
      setUploadState({
        uploading: false,
        errorMessage: `Image exceeds maximum allowed size of ${formatBytes(
          studentAuthUiConfig.profileImageMaxBytes,
        )}.`,
      });
      resetFileInput();
      return;
    }

    const previewUrl = URL.createObjectURL(selectedFile);

    setImageDraft((prev) => {
      if (prev?.originalPreviewUrl) {
        URL.revokeObjectURL(prev.originalPreviewUrl);
      }
      if (
        prev?.workingPreviewUrl &&
        prev.workingPreviewUrl !== prev.originalPreviewUrl
      ) {
        URL.revokeObjectURL(prev.workingPreviewUrl);
      }

      return {
        originalFile: selectedFile,
        originalPreviewUrl: previewUrl,
        workingPreviewUrl: previewUrl,
        workingFile: selectedFile,
        hasUnsavedCrop: false,
      };
    });

    setUploadState({
      uploading: false,
      errorMessage: null,
    });

    setIsPreviewModalOpen(true);
    setIsCropModalOpen(false);
    resetFileInput();
  }

  async function handleEditCurrentImage() {
    if (!effectiveProfileImageUrl || !effectiveCanEditUploadedAvatar) {
      return;
    }

    try {
      setUploadState({
        uploading: true,
        errorMessage: null,
      });

      const response = await fetch(effectiveProfileImageUrl, {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Failed to load current uploaded image.");
      }

      const blob = await response.blob();
      const normalizedType = blob.type || "image/webp";

      if (!isAllowedMimeType(normalizedType)) {
        throw new Error("Current uploaded image type is not supported for editing.");
      }

      const file = new File([blob], "avatar.webp", { type: normalizedType });
      const previewUrl = URL.createObjectURL(file);

      setImageDraft((prev) => {
        if (prev?.originalPreviewUrl) {
          URL.revokeObjectURL(prev.originalPreviewUrl);
        }
        if (
          prev?.workingPreviewUrl &&
          prev.workingPreviewUrl !== prev.originalPreviewUrl
        ) {
          URL.revokeObjectURL(prev.workingPreviewUrl);
        }

        return {
          originalFile: file,
          originalPreviewUrl: previewUrl,
          workingPreviewUrl: previewUrl,
          workingFile: file,
          hasUnsavedCrop: false,
        };
      });

      setIsPreviewModalOpen(true);
      setIsCropModalOpen(false);
      setUploadState({
        uploading: false,
        errorMessage: null,
      });
    } catch (error) {
      setUploadState({
        uploading: false,
        errorMessage:
          error instanceof Error
            ? error.message
            : "Failed to open current uploaded image for editing.",
      });
    }
  }

  async function handleSaveCrop() {
    if (!imageDraft || !cropPixels) {
      setUploadState({
        uploading: false,
        errorMessage: "No crop area is available to save.",
      });
      return;
    }

    try {
      const croppedFile = await createCroppedImageFile(
        imageDraft.originalPreviewUrl,
        cropPixels,
      );

      const croppedPreviewUrl = URL.createObjectURL(croppedFile);

      setImageDraft((prev) => {
        if (!prev) return null;

        if (prev.workingPreviewUrl !== prev.originalPreviewUrl) {
          URL.revokeObjectURL(prev.workingPreviewUrl);
        }

        return {
          ...prev,
          workingPreviewUrl: croppedPreviewUrl,
          workingFile: croppedFile,
          hasUnsavedCrop: true,
        };
      });

      setIsCropModalOpen(false);
      setUploadState({
        uploading: false,
        errorMessage: null,
      });
    } catch (error) {
      setUploadState({
        uploading: false,
        errorMessage:
          error instanceof Error ? error.message : "Failed to apply crop.",
      });
    }
  }

  function handleUnsaveCrop() {
    setImageDraft((prev) => {
      if (!prev) return null;

      if (prev.workingPreviewUrl !== prev.originalPreviewUrl) {
        URL.revokeObjectURL(prev.workingPreviewUrl);
      }

      return {
        ...prev,
        workingPreviewUrl: prev.originalPreviewUrl,
        workingFile: prev.originalFile,
        hasUnsavedCrop: false,
      };
    });

    setIsCropModalOpen(false);
    setUploadState({
      uploading: false,
      errorMessage: null,
    });
  }

  async function handleApplyUpload() {
    if (!imageDraft || !accessToken) {
      setUploadState({
        uploading: false,
        errorMessage: "No image draft is available for upload.",
      });
      return;
    }

    try {
      setUploadState({
        uploading: true,
        errorMessage: null,
      });

      const response = await uploadStudentProfileImage(
        accessToken,
        imageDraft.workingFile,
      );

      setOptimisticUpload({
        profileImageUrl: response.profile_image_url,
        profileImageStorageKey: response.profile_image_storage_key,
      });

      closePreviewModal();

      await Promise.allSettled([
        refreshSession(),
        reloadOnboardingState(),
      ]);
    } catch (error) {
      setUploadState({
        uploading: false,
        errorMessage:
          error instanceof Error ? error.message : "Failed to upload profile image.",
      });
    }
  }

  return {
    fileInputRef,
    uploadState,
    imageDraft,
    previewImageUrl,
    optimisticUpload,
    effectiveProfileImageUrl,
    effectiveCanEditUploadedAvatar,
    isPreviewModalOpen,
    isCropModalOpen,
    crop,
    zoom,
    cropPixels,
    setCrop,
    setZoom,
    setCropPixels,
    handleImageFileSelection,
    handleEditCurrentImage,
    handleApplyUpload,
    handleSaveCrop,
    handleUnsaveCrop,
    openCropModal,
    closePreviewModal,
  };
}