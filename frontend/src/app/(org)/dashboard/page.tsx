import { redirect } from "next/navigation";

import { getSession } from "@/lib/auth/session";

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-8">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Organisation features are enabled per Feature Wiring configuration and will
        render here in later phases.
      </p>
      <a
        className="group mt-4 flex max-w-xl items-center justify-between border border-[#d9d0c2] bg-[#faf7f2] p-5 text-[#26332e] shadow-sm transition hover:border-[#aa6148] hover:shadow-md"
        href="/interior-design"
      >
        <span>
          <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-[#aa6148]">
            Product studio
          </span>
          <span className="mt-1 block font-serif text-2xl">Interior Design AI</span>
          <span className="mt-1 block text-sm text-[#69756f]">
            Upload a room, analyze its architecture, and create design versions.
          </span>
        </span>
        <span aria-hidden="true" className="text-2xl transition group-hover:translate-x-1">
          -&gt;
        </span>
      </a>
      {session.isPlatformAdmin ? (
        <div className="flex gap-4">
          <a className="font-medium text-emerald-700 underline" href="/organisations">
            Manage organisations
          </a>
          <a className="font-medium text-sky-700 underline" href="/ai-registry">
            Manage AI Registry
          </a>
        </div>
      ) : null}
    </div>
  );
}
