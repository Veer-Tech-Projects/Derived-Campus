"use client";

import { useEffect, useState } from "react";

type StudentAccountTheme = "light" | "dark";

const STORAGE_KEY = "derived-campus-theme";

function getSystemTheme(): StudentAccountTheme {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function useStudentAccountTheme() {
  const [theme, setTheme] = useState<StudentAccountTheme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const storedTheme =
      typeof window !== "undefined"
        ? (window.localStorage.getItem(STORAGE_KEY) as StudentAccountTheme | null)
        : null;

    const resolvedTheme =
      storedTheme === "light" || storedTheme === "dark"
        ? storedTheme
        : getSystemTheme();

    setTheme(resolvedTheme);
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || typeof window === "undefined") {
      return;
    }

    const root = window.document.documentElement;

    if (theme === "dark") {
      root.classList.add("dark");
      root.style.colorScheme = "dark";
    } else {
      root.classList.remove("dark");
      root.style.colorScheme = "light";
    }

    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [mounted, theme]);

  function toggleTheme() {
    setTheme((previous) => (previous === "dark" ? "light" : "dark"));
  }

  return {
    mounted,
    theme,
    isDark: theme === "dark",
    toggleTheme,
    setTheme,
  };
}