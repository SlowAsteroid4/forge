import { Suspense } from "react";
import { OpsSidebar } from "@/components/ops/sidebar";

export const metadata = {
  title: "Forge Ops",
};

export default function OpsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full">
      <OpsSidebar />
      <div className="flex flex-col flex-1 min-h-full overflow-hidden">
        <Suspense>{children}</Suspense>
      </div>
    </div>
  );
}
