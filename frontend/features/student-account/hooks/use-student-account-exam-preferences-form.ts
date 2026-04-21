"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  getStudentAccountExamPreferences,
  updateStudentAccountExamPreferences,
} from "../api/student-account-api";
import type { StudentExamPreferenceCatalogItemDTO } from "@/features/student-auth/types/student-auth-contracts";

type UseStudentAccountExamPreferencesFormArgs = {
  accessToken: string | null;
};

const SUCCESS_MESSAGE_TIMEOUT_MS = 3000;

function areSameSelections(left: string[], right: string[]): boolean {
  if (left.length !== right.length) {
    return false;
  }

  const normalizedLeft = [...left].sort();
  const normalizedRight = [...right].sort();

  return normalizedLeft.every((value, index) => value === normalizedRight[index]);
}

export function useStudentAccountExamPreferencesForm({
  accessToken,
}: UseStudentAccountExamPreferencesFormArgs) {
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [availableExams, setAvailableExams] = useState<StudentExamPreferenceCatalogItemDTO[]>([]);
  const [initialSelectedIds, setInitialSelectedIds] = useState<string[]>([]);
  const [selectedExamIds, setSelectedExamIds] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
        successTimeoutRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!accessToken) {
      setLoading(false);
      setSubmitError("No student access token is available.");
      return;
    }

    const validatedAccessToken = accessToken;
    let cancelled = false;

    async function loadState() {
      try {
        setLoading(true);
        setSubmitError(null);

        const response = await getStudentAccountExamPreferences(validatedAccessToken);

        if (cancelled) {
          return;
        }

        setAvailableExams(response.available_exam_preferences);
        setInitialSelectedIds(response.selected_exam_preference_catalog_ids);
        setSelectedExamIds(response.selected_exam_preference_catalog_ids);
      } catch (error) {
        if (cancelled) {
          return;
        }

        setSubmitError(
          error instanceof Error
            ? error.message
            : "Failed to load exam preferences.",
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadState();

    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  const dirty = useMemo(() => {
    return !areSameSelections(selectedExamIds, initialSelectedIds);
  }, [selectedExamIds, initialSelectedIds]);

  const validationError = useMemo(() => {
    if (selectedExamIds.length === 0) {
      return "Please select at least one exam preference.";
    }

    return null;
  }, [selectedExamIds]);

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
    setSelectedExamIds(initialSelectedIds);
    setSubmitError(null);
    setSubmitSuccess(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    clearSuccessTimeout();
    setSelectedExamIds(initialSelectedIds);
    setSubmitError(null);
    setSubmitSuccess(null);
    setSubmitting(false);
    setIsEditing(false);
  }

  function toggleExam(examId: string) {
    clearSuccessTimeout();
    setSubmitError(null);
    setSubmitSuccess(null);

    setSelectedExamIds((previous) => {
      const isSelected = previous.includes(examId);

      if (isSelected) {
        return previous.filter((id) => id !== examId);
      }

      return [...previous, examId];
    });
  }

  async function saveChanges() {
    if (selectedExamIds.length === 0) {
      clearSuccessTimeout();
      setSubmitError("Please select at least one exam preference.");
      setSubmitSuccess(null);
      return;
    }

    if (!accessToken) {
      clearSuccessTimeout();
      setSubmitError("No student access token is available.");
      setSubmitSuccess(null);
      return;
    }

    try {
      clearSuccessTimeout();
      setSubmitting(true);
      setSubmitError(null);
      setSubmitSuccess(null);

      const response = await updateStudentAccountExamPreferences(accessToken, {
        exam_preference_catalog_ids: selectedExamIds,
      });

      setInitialSelectedIds(response.selected_exam_preference_catalog_ids);
      setSelectedExamIds(response.selected_exam_preference_catalog_ids);

      setSubmitSuccess("Exam preferences updated successfully.");
      setIsEditing(false);
      scheduleSuccessDismiss();
    } catch (error) {
      clearSuccessTimeout();
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Failed to update exam preferences.",
      );
      setSubmitSuccess(null);
    } finally {
      setSubmitting(false);
    }
  }

  return {
    loading,
    isEditing,
    availableExams,
    selectedExamIds,
    validationError,
    dirty,
    submitting,
    submitError,
    submitSuccess,
    startEditing,
    cancelEditing,
    toggleExam,
    saveChanges,
  };
}