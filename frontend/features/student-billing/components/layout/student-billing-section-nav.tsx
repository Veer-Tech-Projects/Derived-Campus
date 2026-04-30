"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type BillingSectionNavItem = {
  href: string;
  label: string;
};

const BILLING_SECTION_NAV_ITEMS: BillingSectionNavItem[] = [
  { href: "/student-billing", label: "Home" },
  { href: "/student-billing/overview", label: "Overview" },
  { href: "/student-billing/plans", label: "Subscriptions" },
  { href: "/student-billing/wallet", label: "Wallet" },
  { href: "/student-billing/history", label: "History" },
];

function isActivePath(currentPath: string, href: string): boolean {
  if (href === "/student-billing") {
    return currentPath === href;
  }

  return currentPath === href || currentPath.startsWith(`${href}/`);
}

export function StudentBillingSectionNav() {
  const pathname = usePathname();

  return (
    <div className="rounded-[1.5rem] border border-border bg-card p-2 shadow-sm">
      <nav
        aria-label="Billing sections"
        className="flex flex-wrap items-center gap-2"
      >
        {BILLING_SECTION_NAV_ITEMS.map((item) => {
          const active = isActivePath(pathname, item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "inline-flex items-center justify-center rounded-[1rem] px-4 py-2.5 text-sm font-semibold transition-all",
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              ].join(" ")}
              aria-current={active ? "page" : undefined}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}