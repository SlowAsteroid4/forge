export const metadata = {
  title: "Forge Arena",
};

export default function ArenaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-full bg-zinc-950 text-zinc-50">
      {children}
    </div>
  );
}
