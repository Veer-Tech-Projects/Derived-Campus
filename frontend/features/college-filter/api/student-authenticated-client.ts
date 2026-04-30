"use client";

import axios, { type AxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * Dedicated authenticated student API client helpers for protected student routes.
 *
 * Design rules:
 * - no admin auth coupling
 * - bearer token supplied explicitly by caller
 * - no hidden token storage assumptions
 * - request helpers remain thin and deterministic
 */
export const studentAuthenticatedClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: false,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

export function buildStudentAuthConfig(
  accessToken: string,
  config?: AxiosRequestConfig,
): AxiosRequestConfig {
  return {
    ...(config ?? {}),
    headers: {
      ...(config?.headers ?? {}),
      Authorization: `Bearer ${accessToken}`,
    },
  };
}