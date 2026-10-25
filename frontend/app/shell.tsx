"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navigation = [
  { href: "/inbox", label: "Inkorg" },
  { href: "/orders", label: "Ordrar" },
  { href: "/plan", label: "Planering" },
  { href: "/fleet", label: "Flotta" },
  { href: "/approve", label: "Godkänn" },
  { href: "/login", label: "Logga in" },
];

/** Trafikledarens sidomeny. Förarnas sidor visas utan meny, i full bredd på mobilen. */
export default function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname.startsWith("/driver/")) {
    return <main className="driver-main">{children}</main>;
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <Link className="brand" href="/inbox">
          AI Trafikledning
        </Link>
        <nav aria-label="Huvudmeny">
          {navigation.map((item) => (
            <Link className={pathname === item.href ? "nav-link active" : "nav-link"} href={item.href} key={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
        <p className="sidebar-note">Lokal utvecklingsversion</p>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
