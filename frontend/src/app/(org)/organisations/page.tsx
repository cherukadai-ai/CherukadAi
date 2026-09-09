import { redirect } from "next/navigation";

import { OrganisationAdmin } from "@/components/organisation-admin";
import { getSession } from "@/lib/auth/session";

export default async function OrganisationsPage() {
  const session = await getSession();
  if (!session?.isPlatformAdmin) {
    redirect("/dashboard");
  }
  return <OrganisationAdmin />;
}