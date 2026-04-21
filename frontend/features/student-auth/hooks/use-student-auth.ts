"use client";

import { useStudentAuthContext } from "../providers/student-auth-provider";

export function useStudentAuth() {
  return useStudentAuthContext();
}