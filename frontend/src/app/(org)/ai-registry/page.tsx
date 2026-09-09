import { redirect } from "next/navigation";

import { AIRegistryAdmin } from "@/components/ai-registry-admin";
import { getSession } from "@/lib/auth/session";

export default async function AIRegistryPage() {
  const session = await getSession();
  if (!session?.isPlatformAdmin) redirect("/dashboard");
  return <AIRegistryAdmin />;
}