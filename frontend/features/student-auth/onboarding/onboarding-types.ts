export type OnboardingStep = 1 | 2 | 3;

export type OnboardingFormState = {
  firstName: string;
  lastName: string;
  displayName: string;
  phoneNumber: string;
  selectedExamIds: string[];
};

export type OnboardingSubmitState = {
  submitting: boolean;
  errorMessage: string | null;
};

export type ProfileImageUploadState = {
  uploading: boolean;
  errorMessage: string | null;
};

export type ImageDraftState = {
  originalFile: File;
  originalPreviewUrl: string;
  workingPreviewUrl: string;
  workingFile: File;
  hasUnsavedCrop: boolean;
};