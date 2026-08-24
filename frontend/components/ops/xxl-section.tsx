import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { XxlWorklistItem } from "@/lib/types/cp-worklist";

interface Props {
  items: XxlWorklistItem[];
  jiraBaseUrl: string | null;
}

/** XXL detectadas — talla rechazada, requieren ruptura. Read-only (WP-24). */
export function XxlSection({ items, jiraBaseUrl }: Props) {
  return (
    <div className="rounded-md border border-destructive/40 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border bg-destructive/10">
        <p className="text-xs text-muted-foreground">
          Estas subtasks tienen talla XXL: no se aceptan y su CP no se lockea.
          Deben dividirse en subtasks más pequeñas (máximo permitido: XL, 8 CP).
        </p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Key</TableHead>
            <TableHead>Summary</TableHead>
            <TableHead>Área</TableHead>
            <TableHead>Player</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.jira_key}>
              <TableCell className="font-mono text-xs">
                {jiraBaseUrl ? (
                  <a
                    href={`${jiraBaseUrl}/browse/${item.jira_key}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline text-primary"
                  >
                    {item.jira_key}
                  </a>
                ) : (
                  item.jira_key
                )}
              </TableCell>
              <TableCell className="text-sm max-w-xs">
                <span className="line-clamp-2">{item.summary}</span>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">{item.area}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {item.assignee_name ?? "—"}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">{item.status}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
