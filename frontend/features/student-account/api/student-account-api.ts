import {
  executeStudentJsonRequest,
} from "@/features/student-auth/api/student-auth-api";
import type {
  StudentExamPreferenceCatalogItemDTO,
  StudentProfileDTO,
} from "@/features/student-auth/types/student-auth-contracts";

export type UpdateStudentAccountProfileRequest = {
  first_name: string;
  last_name: string;
  display_name: string | null;
};

export type UpdateStudentAccountProfileResponse = {
  success: boolean;
  profile: StudentProfileDTO;
};

export type UpdateStudentAccountPhoneRequest = {
  phone_number: string;
};

export type UpdateStudentAccountPhoneResponse = {
  success: boolean;
  profile: StudentProfileDTO;
};

export type StudentAccountExamPreferencesStateResponse = {
  available_exam_preferences: StudentExamPreferenceCatalogItemDTO[];
  selected_exam_preference_catalog_ids: string[];
};

export type UpdateStudentAccountExamPreferencesRequest = {
  exam_preference_catalog_ids: string[];
};

export type UpdateStudentAccountExamPreferencesResponse = {
  success: boolean;
  selected_exam_preference_catalog_ids: string[];
};

export async function updateStudentAccountProfile(
  accessToken: string,
  payload: UpdateStudentAccountProfileRequest,
): Promise<UpdateStudentAccountProfileResponse> {
  return executeStudentJsonRequest<UpdateStudentAccountProfileResponse>(
    "/student-account/profile",
    {
      method: "PATCH",
      accessToken,
      body: payload,
    },
  );
}

export async function updateStudentAccountPhone(
  accessToken: string,
  payload: UpdateStudentAccountPhoneRequest,
): Promise<UpdateStudentAccountPhoneResponse> {
  return executeStudentJsonRequest<UpdateStudentAccountPhoneResponse>(
    "/student-account/phone",
    {
      method: "PATCH",
      accessToken,
      body: payload,
    },
  );
}

export async function getStudentAccountExamPreferences(
  accessToken: string,
): Promise<StudentAccountExamPreferencesStateResponse> {
  return executeStudentJsonRequest<StudentAccountExamPreferencesStateResponse>(
    "/student-account/exam-preferences",
    {
      accessToken,
    },
  );
}

export async function updateStudentAccountExamPreferences(
  accessToken: string,
  payload: UpdateStudentAccountExamPreferencesRequest,
): Promise<UpdateStudentAccountExamPreferencesResponse> {
  return executeStudentJsonRequest<UpdateStudentAccountExamPreferencesResponse>(
    "/student-account/exam-preferences",
    {
      method: "PATCH",
      accessToken,
      body: payload,
    },
  );
}