"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  LayoutDashboard,
  CheckSquare,
  AlertTriangle,
  Flag,
  TrendingUp,
  DollarSign,
  Users,
  Settings,
  Plug,
  FileText,
  ChevronDown,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
  disabled?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Dashboard",
    items: [
      {
        label: "Sprint actual",
        href: "/dashboard",
        icon: <LayoutDashboard size={16} />,
      },
    ],
  },
  {
    title: "Operación",
    items: [
      {
        label: "Aprobaciones CP",
        href: "/operations/cp-approvals",
        icon: <CheckSquare size={16} />,
        disabled: true,
      },
      {
        label: "Penalizaciones",
        href: "/operations/penalties",
        icon: <AlertTriangle size={16} />,
        disabled: true,
      },
      {
        label: "Cerrar sprint",
        href: "/operations/close-sprint",
        icon: <Flag size={16} />,
        disabled: true,
      },
    ],
  },
  {
    title: "Analítica",
    items: [
      {
        label: "Forecast",
        href: "/analytics/forecast",
        icon: <TrendingUp size={16} />,
        disabled: true,
      },
      {
        label: "Costo por área",
        href: "/analytics/costs",
        icon: <DollarSign size={16} />,
        disabled: true,
      },
    ],
  },
  {
    title: "Administración",
    items: [
      {
        label: "Players",
        href: "/admin/players",
        icon: <Users size={16} />,
        disabled: true,
      },
      {
        label: "Integraciones",
        href: "/admin/integrations",
        icon: <Plug size={16} />,
      },
      {
        label: "Motor",
        href: "/admin/engine",
        icon: <Settings size={16} />,
        disabled: true,
      },
      {
        label: "Audit log",
        href: "/admin/audit",
        icon: <FileText size={16} />,
        disabled: true,
      },
    ],
  },
];

export function OpsSidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col w-56 min-h-screen border-r border-border bg-background py-4">
      {/* Logo */}
      <div className="px-4 mb-6">
        <span className="text-xs font-bold tracking-widest text-muted-foreground uppercase">
          Forge
        </span>
        <h1 className="text-base font-semibold text-foreground">Ops Console</h1>
      </div>

      {/* Nav sections */}
      <div className="flex-1 px-2 space-y-4">
        {navSections.map((section) => (
          <div key={section.title}>
            <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              {section.title}
            </p>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <li key={item.href}>
                    {item.disabled ? (
                      <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground/50 cursor-not-allowed rounded-md select-none">
                        {item.icon}
                        <span>{item.label}</span>
                      </div>
                    ) : (
                      <Link
                        href={item.href}
                        className={cn(
                          "flex items-center gap-2 px-2 py-1.5 text-sm rounded-md transition-colors",
                          isActive
                            ? "bg-accent text-accent-foreground font-medium"
                            : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                        )}
                      >
                        {item.icon}
                        <span className="flex-1">{item.label}</span>
                        {item.badge != null && item.badge > 0 && (
                          <Badge variant="destructive" className="h-4 px-1 text-[10px]">
                            {item.badge}
                          </Badge>
                        )}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      {/* Footer: link to Arena */}
      <div className="px-4 pt-4 border-t border-border">
        <Link
          href="/arena/login"
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronDown size={12} className="-rotate-90" />
          Ir a Forge Arena
        </Link>
      </div>
    </nav>
  );
}
