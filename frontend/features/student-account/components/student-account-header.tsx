"use client";

import { ArrowLeft } from "lucide-react";
import { StudentAccountSettingsMenu } from "./student-account-settings-menu";

type StudentAccountHeaderProps = {
  title: string;
  subtitle?: string;
  onLogout: () => void | Promise<void>;
  loggingOut?: boolean;
};

function HeroIconButton({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground shadow-sm backdrop-blur-md transition hover:bg-primary-foreground/20"
    >
      {children}
    </button>
  );
}

export function StudentAccountHeader({
  title,
  onLogout,
  loggingOut = false,
}: StudentAccountHeaderProps) {
  return (
    <div className="relative z-20 flex items-start justify-between gap-3 sm:gap-4">
      <HeroIconButton>
        <ArrowLeft className="h-5 w-5 sm:h-6 sm:w-6" />
      </HeroIconButton>

      <div className="min-w-0 flex-1 px-2 text-center">
        <h1 className="mx-auto max-w-[12rem] text-xl font-semibold leading-tight tracking-tight text-primary-foreground sm:max-w-none sm:text-2xl">
          {title}
        </h1>
      </div>

      <StudentAccountSettingsMenu
        onLogout={onLogout}
        loggingOut={loggingOut}
      />
    </div>
  );
}