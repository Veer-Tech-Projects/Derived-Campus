"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function StudentBillingHomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/student-account?tab=billing");
  }, [router]);

  return null;
}