"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { updateStudentAccountProfile } from "../api/student-account-api";
import type { StudentProfileDTO } from "@/features/student-auth/types/student-auth-contracts";

type StudentAccountProfileFormValues = {
  firstName: string;
  lastName: string;
  displayName: string;
};

type UseStudentAccountProfileFormArgs = {
  accessToken: string | null;
  profile: StudentProfileDTO | null;
  refreshSession: () => Promise<void>;
};

type ValidationErrors = {
  firstName: string | null;
  lastName: string | null;
  displayName: string | null;
};

const FIRST_NAME_MAX_LENGTH = 100;
const LAST_NAME_MAX_LENGTH = 100;
const DISPLAY_NAME_MAX_LENGTH = 200;
const SUCCESS_MESSAGE_TIMEOUT_MS = 3000;

function buildInitialValues(
  profile: StudentProfileDTO | null,
): StudentAccountProfileFormValues {
  return {
    firstName: profile?.first_name ?? "",
    lastName: profile?.last_name ?? "",
    displayName: profile?.display_name ?? "",
  };
}

function validateValues(
  values: StudentAccountProfileFormValues,
): ValidationErrors {
  const firstName = values.firstName.trim();
  const lastName = values.lastName.trim();
  const displayName = values.displayName.trim();

  return {
    firstName:
      firstName.length === 0
        ? "First name is required."
        : firstName.length > FIRST_NAME_MAX_LENGTH
          ? "First name cannot exceed 100 characters."
          : null,
    lastName:
      lastName.length === 0
        ? "Last name is required."
        : lastName.length > LAST_NAME_MAX_LENGTH
          ? "Last name cannot exceed 100 characters."
          : null,
    displayName:
      displayName.length > DISPLAY_NAME_MAX_LENGTH
        ? "Display name cannot exceed 200 characters."
        : null,
  };
}

function hasValidationErrors(errors: ValidationErrors): boolean {
  return Boolean(
    errors.firstName || errors.lastName || errors.displayName,
  );
}

export function useStudentAccountProfileForm({
  accessToken,
  profile,
  refreshSession,
}: UseStudentAccountProfileFormArgs) {
  const [isEditing, setIsEditing] = useState(false);
  const [values, setValues] = useState<StudentAccountProfileFormValues>(
    buildInitialValues(profile),
  );
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isEditing) {
      setValues(buildInitialValues(profile));
    }
  }, [profile, isEditing]);

  useEffect(() => {
    return () => {
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
        successTimeoutRef.current = null;
      }
    };
  }, []);

  const validationErrors = useMemo(() => validateValues(values), [values]);

  const dirty = useMemo(() => {
    const initial = buildInitialValues(profile);

    return (
      values.firstName !== initial.firstName ||
      values.lastName !== initial.lastName ||
      values.displayName !== initial.displayName
    );
  }, [profile, values]);

  function clearSuccessTimeout() {
    if (successTimeoutRef.current) {
      clearTimeout(successTimeoutRef.current);
      successTimeoutRef.current = null;
    }
  }

  function scheduleSuccessDismiss() {
    clearSuccessTimeout();

    successTimeoutRef.current = setTimeout(() => {
      setSubmitSuccess(null);
      successTimeoutRef.current = null;
    }, SUCCESS_MESSAGE_TIMEOUT_MS);
  }

  function updateField<K extends keyof StudentAccountProfileFormValues>(
    key: K,
    value: StudentAccountProfileFormValues[K],
  ) {
    clearSuccessTimeout();
    setValues((previous) => ({
      ...previous,
      [key]: value,
    }));
    setSubmitError(null);
    setSubmitSuccess(null);
  }

  function startEditing() {
    clearSuccessTimeout();
    setValues(buildInitialValues(profile));
    setSubmitError(null);
    setSubmitSuccess(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    clearSuccessTimeout();
    setValues(buildInitialValues(profile));
    setSubmitError(null);
    setSubmitSuccess(null);
    setSubmitting(false);
    setIsEditing(false);
  }

  async function saveChanges() {
    const errors = validateValues(values);

    if (hasValidationErrors(errors)) {
      clearSuccessTimeout();
      setSubmitError("Please correct the highlighted fields before saving.");
      setSubmitSuccess(null);
      return;
    }

    if (!accessToken) {
      clearSuccessTimeout();
      setSubmitError("No student access token is available.");
      setSubmitSuccess(null);
      return;
    }

    if (!profile) {
      clearSuccessTimeout();
      setSubmitError("Student profile is not available.");
      setSubmitSuccess(null);
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);
      clearSuccessTimeout();

      await updateStudentAccountProfile(accessToken, {
        first_name: values.firstName.trim(),
        last_name: values.lastName.trim(),
        display_name: values.displayName.trim() || null,
      });

      await refreshSession();

      setSubmitSuccess("Profile details updated successfully.");
      setIsEditing(false);
      scheduleSuccessDismiss();
    } catch (error) {
      clearSuccessTimeout();
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Failed to update student account profile.",
      );
      setSubmitSuccess(null);
    } finally {
      setSubmitting(false);
    }
  }

  return {
    isEditing,
    values,
    validationErrors,
    dirty,
    submitting,
    submitError,
    submitSuccess,
    startEditing,
    cancelEditing,
    updateField,
    saveChanges,
  };
}