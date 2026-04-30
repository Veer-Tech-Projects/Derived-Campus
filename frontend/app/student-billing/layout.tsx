"use client";

import type { ReactNode } from "react";

type StudentBillingLayoutProps = {
  children: ReactNode;
};

export default function StudentBillingLayout({
  children,
}: StudentBillingLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        {children}
      </div>
    </div>
  );
}