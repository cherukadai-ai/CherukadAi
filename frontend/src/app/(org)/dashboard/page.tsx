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
