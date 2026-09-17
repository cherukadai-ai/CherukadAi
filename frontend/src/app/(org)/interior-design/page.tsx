import { redirect } from "next/navigation";

import { InteriorDesignStudio } from "@/components/interior-design-studio";
import { getSession } from "@/lib/auth/session";

export default async function InteriorDesignPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  return <InteriorDesignStudio />;
}
