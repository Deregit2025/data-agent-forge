"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const links = [
  { href: "/",            label: "Dashboard" },
  { href: "/benchmark",   label: "Benchmark" },
  { href: "/demo",        label: "Live Demo" },
  { href: "/probes",      label: "Probes" },
  { href: "/corrections", label: "Corrections" },
  { href: "/architecture",label: "Architecture" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-forge-bg/90 backdrop-blur border-b border-forge-border">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-14">
        {/* logo */}
        <Link href="/" className="flex items-center gap-2 font-mono font-semibold text-forge-amber">
          <span className="text-lg">⚙</span>
          <span>Oracle<span className="text-white"> Forge</span></span>
        </Link>

        {/* links */}
        <div className="flex items-center gap-1">
          {links.map(l => (
            <Link
              key={l.href}
              href={l.href}
              className={clsx(
                "px-3 py-1.5 rounded text-sm font-medium transition-colors",
                path === l.href
                  ? "bg-forge-amber text-forge-bg"
                  : "text-forge-muted hover:text-forge-text hover:bg-forge-surface"
              )}
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* score badge */}
        <div className="flex items-center gap-2 font-mono text-sm">
          <span className="text-forge-muted">Pass@1</span>
          <span className="px-2 py-0.5 rounded bg-forge-amber/10 text-forge-amber border border-forge-amber/30 font-semibold">
            44.4%
          </span>
          <span className="text-forge-muted">vs</span>
          <span className="text-forge-muted">38%</span>
        </div>
      </div>
    </nav>
  );
}
