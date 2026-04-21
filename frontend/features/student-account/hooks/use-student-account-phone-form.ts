"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { updateStudentAccountPhone } from "../api/student-account-api";
import type { StudentProfileDTO } from "@/features/student-auth/types/student-auth-contracts";

type UseStudentAccountPhoneFormArgs = {
  accessToken: string | null;
  profile: StudentProfileDTO | null;
  refreshSession: () => Promise<void>;
};

type ValidationResult = {
  error: string | null;
};

const PHONE_DIGIT_LENGTH = 10;
const SUCCESS_MESSAGE_TIMEOUT_MS = 3000;

function buildInitialValue(profile: StudentProfileDTO | null): string {
  const raw = profile?.phone_number_e164?.trim() ?? "";

  if (!raw) {
    return "";
  }

  if (raw.startsWith("+91") && raw.length >= 13) {
    return raw.slice(3);
  }

  return raw.replace(/\D/g, "").slice(-PHONE_DIGIT_LENGTH);
}

function sanitizePhoneInput(value: string): string {
  return value.replace(/\D/g, "").slice(0, PHONE_DIGIT_LENGTH);
}

function validatePhoneValue(value: string): ValidationResult {
  if (value.length === 0) {
    return {
      error: "Phone number is required.",
    };
  }

  if (value.length !== PHONE_DIGIT_LENGTH) {
    return {
      error: "Phone number must contain exactly 10 digits.",
    };
  }

  return {
    error: null,
  };
}

export function useStudentAccountPhoneForm({
  accessToken,
  profile,
  refreshSession,
}: UseStudentAccountPhoneFormArgs) {
  const [isEditing, setIsEditing] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState<string>(buildInitialValue(profile));
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isEditing) {
      setPhoneNumber(buildInitialValue(profile));
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

  const validation = useMemo(() => validatePhoneValue(phoneNumber), [phoneNumber]);

  const dirty = useMemo(() => {
    return phoneNumber !== buildInitialValue(profile);
  }, [phoneNumber, profile]);

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

  function startEditing() {
    clearSuccessTimeout();
    setPhoneNumber(buildInitialValue(profile));
    setSubmitError(null);
    setSubmitSuccess(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    clearSuccessTimeout();
    setPhoneNumber(buildInitialValue(profile));
    setSubmitError(null);
    setSubmitSuccess(null);
    setSubmitting(false);
    setIsEditing(false);
  }

  function updatePhoneNumber(value: string) {
    clearSuccessTimeout();
    setPhoneNumber(sanitizePhoneInput(value));
    setSubmitError(null);
    setSubmitSuccess(null);
  }

  async function saveChanges() {
    const result = validatePhoneValue(phoneNumber);

    if (result.error) {
      clearSuccessTimeout();
      setSubmitError(result.error);
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
      clearSuccessTimeout();
      setSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);

      await updateStudentAccountPhone(accessToken, {
        phone_number: phoneNumber,
      });

      await refreshSession();

      setSubmitSuccess("Phone number updated successfully.");
      setIsEditing(false);
      scheduleSuccessDismiss();
    } catch (error) {
      clearSuccessTimeout();
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Failed to update phone number.",
      );
      setSubmitSuccess(null);
    } finally {
      setSubmitting(false);
    }
  }

  return {
    isEditing,
    phoneNumber,
    validationError: validation.error,
    dirty,
    submitting,
    submitError,
    submitSuccess,
    startEditing,
    cancelEditing,
    updatePhoneNumber,
    saveChanges,
  };
}