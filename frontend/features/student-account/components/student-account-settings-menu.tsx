"use client";

import { useEffect, useRef, useState } from "react";
import { LogOut, Moon, Settings2, Sun } from "lucide-react";
import { useStudentAccountTheme } from "../hooks/use-student-account-theme";

type StudentAccountSettingsMenuProps = {
  onLogout: () => void | Promise<void>;
  loggingOut?: boolean;
};

export function StudentAccountSettingsMenu({
  onLogout,
  loggingOut = false,
}: StudentAccountSettingsMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const { mounted, isDark, toggleTheme } = useStudentAccountTheme();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!menuRef.current) {
        return;
      }

      if (!menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  return (
    <div className="relative z-30" ref={menuRef}>
      <button
        type="button"
        aria-label="Open account settings"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground shadow-sm backdrop-blur-md transition hover:bg-primary-foreground/20"
      >
        <Settings2 className="h-5 w-5 sm:h-6 sm:w-6" />
      </button>

      {open ? (
        <div className="absolute right-0 top-14 w-[calc(100vw-2rem)] max-w-[18rem] overflow-hidden rounded-[1.6rem] border border-border bg-card shadow-[0_22px_60px_rgba(0,0,0,0.18)] sm:w-72">
          <div className="border-b border-border px-4 py-4">
            <p className="text-sm font-semibold text-foreground">
              Account options
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Quick controls for appearance and session management.
            </p>
          </div>

          <div className="p-2">
            <button
              type="button"
              onClick={() => {
                toggleTheme();
                setOpen(false);
              }}
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium text-foreground transition hover:bg-secondary"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-background text-foreground shadow-sm">
                {mounted && isDark ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </span>

              <span className="flex-1">
                {mounted && isDark
                  ? "Switch to light mode"
                  : "Switch to dark mode"}
              </span>
            </button>

            <button
              type="button"
              onClick={() => {
                setOpen(false);
                void onLogout();
              }}
              disabled={loggingOut}
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium text-foreground transition hover:bg-secondary disabled:pointer-events-none disabled:opacity-60"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-background text-foreground shadow-sm">
                <LogOut className="h-4 w-4" />
              </span>

              <span className="flex-1">
                {loggingOut ? "Signing out..." : "Logout"}
              </span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}