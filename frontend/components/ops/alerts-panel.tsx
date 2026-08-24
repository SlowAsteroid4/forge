import { Clock, Users, CheckSquare, Bug, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DashboardAlert } from "@/lib/types/dashboard";

const ALERT_ICONS: Record<string, React.ReactNode> = {
  abandoned_subtask: <Clock size={14} />,
  waiting_long: <Clock size={14} />,
  waiting_no_ticket: <Clock size={14} />,
  wip_exceeded: <Users size={14} />,
  xxl_detected: <CheckSquare size={14} />,
  derived_bug_unresolved: <Bug size={14} />,
};

const SEVERITY_STYLES: Record<string, string> = {
  warning: "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
  error:   "border-red-300 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-950/40 dark:text-red-300",
  info:    "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
  high:    "border-red-300 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-950/40 dark:text-red-300",
  medium:  "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
  low:     "border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
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
