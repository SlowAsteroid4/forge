import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { KpiValueFull } from "@/lib/types/dashboard";

interface KpiCardProps {
  title: string;
  value: number | KpiValueFull;
  decimals?: number;
  invertDelta?: boolean;
}

export function KpiCard({ title, value, decimals = 0, invertDelta = false }: KpiCardProps) {
  const numValue = typeof value === "number" ? value : value.value;
  const delta = typeof value === "object" ? value.delta_pct : undefined;
  const previousValue = typeof value === "object" ? value.previous_value : undefined;

  const hasDelta = delta != null;
  const isPositive = hasDelta && (invertDelta ? delta < 0 : delta > 0);
  const isNegative = hasDelta && (invertDelta ? delta > 0 : delta < 0);

  return (
    <Card>
      <CardHeader className="pb-1 pt-4 px-4">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="flex items-end gap-2">
          <span className="text-3xl font-bold tabular-nums">
            {numValue.toFixed(decimals)}
          </span>
          {hasDelta && (
            <div
              className={cn(
                "flex items-center gap-0.5 text-xs font-medium mb-1",
                isPositive && "text-green-600",
                isNegative && "text-red-500",
                !isPositive && !isNegative && "text-muted-foreground",
              )}
            >
              {isPositive ? (
                <TrendingUp size={12} />
              ) : isNegative ? (
                <TrendingDown size={12} />
              ) : (
                <Minus size={12} />
              )}
              <span>{Math.abs(delta!).toFixed(1)}%</span>
            </div>
          )}
        </div>
        {previousValue != null && (
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Sprint anterior: {previousValue.toFixed(decimals)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
