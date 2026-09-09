import { redirect } from "next/navigation";

import { FeatureWiringAdmin } from "@/components/feature-wiring-admin";
import { getSession } from "@/lib/auth/session";

export default async function OrganisationAIFeaturesPage({
  params,
}: {
  params: Promise<{ organisationId: string }>;
}) {
  const session = await getSession();
  if (!session?.isPlatformAdmin) redirect("/dashboard");
  const { organisationId } = await params;
  return <FeatureWiringAdmin organisationId={organisationId} />;
}