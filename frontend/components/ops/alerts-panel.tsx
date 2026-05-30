import { Clock, Users, CheckSquare, Bug, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DashboardAlert } from "@/lib/types/dashboard";

const ALERT_ICONS: Record<string, React.ReactNode> = {
  abandoned_subtask: <Clock size={14} />,
  waiting_long: <Clock size={14} />,
  waiting_no_ticket: <Clock size={14} />,
  wip_exceeded: <Users size={14} />,
  cp_pending_approval: <CheckSquare size={14} />,
  derived_bug_unresolved: <Bug size={14} />,
};

const SEVERITY_STYLES: Record<string, string> = {
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  error: "border-red-200 bg-red-50 text-red-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
  high: "border-red-200 bg-red-50 text-red-800",
  medium: "border-amber-200 bg-amber-50 text-amber-800",
  low: "border-blue-200 bg-blue-50 text-blue-800",
};

interface AlertsPanelProps {
  alerts: DashboardAlert[];
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  if (alerts.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-2">
        ✓ Sin alertas activas en este sprint.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert, i) => (
        <div
          key={i}
          className={cn(
            "flex items-start gap-2 px-3 py-2 rounded-md border text-sm",
            SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.warning,
          )}
        >
          <span className="mt-0.5 shrink-0">
            {ALERT_ICONS[alert.alert_type] ?? <AlertTriangle size={14} />}
          </span>
          <span>{alert.message}</span>
        </div>
      ))}
    </div>
  );
}
