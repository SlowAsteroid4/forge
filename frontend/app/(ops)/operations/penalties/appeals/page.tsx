import { api } from "@/lib/api";
import type { PendingAppealsResponse } from "@/lib/types/penalties";
import { AppealsClient } from "./AppealsClient";

async function getPendingAppeals(): Promise<PendingAppealsResponse> {
  return api
    .get<PendingAppealsResponse>("/penalties/appeals/pending")
    .catch(() => ({ total: 0, items: [] }));
}

export default async function PendingAppealsPage() {
  const data = await getPendingAppeals();

  return (
    <div className="flex flex-col flex-1 overflow-auto">
      <div className="flex-1 p-6 space-y-6">
        <AppealsClient items={data.items} total={data.total} />
      </div>
    </div>
  );
}
