"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Building2, CheckCircle2, ChevronRight, Inbox, Loader2, Plus, Search, ShieldCheck } from "lucide-react";

import { ApiError, apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Organisation = {
  id: string;
  name: string;
  display_name: string;
  email: string;
  status: string;
};

export function OrganisationAdmin() {
  const router = useRouter();
  const [items, setItems] = useState<Organisation[]>([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ name: "", display_name: "", email: "" });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [created, setCreated] = useState(false);

  async function loadOrganisations(value = search) {
    setIsLoading(true);
    try {
      const response = await apiClient.get<{ items: Organisation[] }>(
        `/organisations${value ? `?search=${encodeURIComponent(value)}` : ""}`,
      );
      setItems(response.items);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    async function loadInitialOrganisations() {
      try {
        const response = await apiClient.get<{ items: Organisation[] }>("/organisations");
        setItems(response.items);
      } catch (requestError) {
        if (requestError instanceof ApiError && requestError.status === 401) {
          router.replace("/login");
          return;
        }
        setError(requestError instanceof ApiError && requestError.status === 403
          ? "Your account does not have platform administrator permissions."
          : "Unable to load organisations.");
      } finally {
        setIsLoading(false);
      }
    }

    void loadInitialOrganisations();
  }, [router]);

  async function createOrganisation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCreated(false);
    setIsCreating(true);
    try {
      await apiClient.post("/organisations/create", form);
      setForm({ name: "", display_name: "", email: "" });
      setCreated(true);
      await loadOrganisations();
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        router.replace("/login");
        return;
      }
      setError(requestError instanceof ApiError && requestError.status === 403
        ? "Your account does not have platform administrator permissions."
        : requestError instanceof ApiError && requestError.status === 404
          ? "The organisations API could not be found. Restart the backend service and try again."
          : requestError instanceof ApiError ? requestError.message : "Unable to create organisation.");
    } finally {
      setIsCreating(false);
    }
  }

  async function changeStatus(id: string, action: "activate" | "suspend" | "archive") {
    await apiClient.post(`/organisations/${id}/${action}`);
    await loadOrganisations();
  }

  return (
    <main className="min-h-full flex-1 bg-[radial-gradient(circle_at_top_right,_#dff8ee,_transparent_34%),linear-gradient(135deg,_#f8faf9_0%,_#eef5f2_100%)] px-5 py-7 sm:px-8 lg:px-12">
      <header className="mx-auto max-w-7xl">
        <div className="flex items-center gap-3 text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">
          <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-100"><Building2 className="size-4" /></span>
          Platform control
        </div>
        <div className="mt-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950">Organisations</h1>
            <p className="mt-2 max-w-xl text-slate-600">Create and steward the workspaces that power your teams.</p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-white/70 px-4 py-2 text-sm text-slate-600 shadow-sm">
            <ShieldCheck className="size-4 text-emerald-600" /> Platform admin
          </div>
        </div>
      </header>
      <section className="mx-auto mt-9 grid max-w-7xl gap-6 lg:grid-cols-[minmax(0,1fr)_25rem]">
        <Card className="border-slate-200/80 bg-white/85 shadow-[0_20px_55px_-35px_rgba(15,23,42,0.35)] backdrop-blur">
          <CardHeader className="border-b border-slate-100 pb-5"><CardTitle className="flex items-center justify-between text-lg"><span>Organisation directory</span><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">{items.length} total</span></CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input className="pl-9" aria-label="Search organisations" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name or email" onKeyDown={(event) => { if (event.key === "Enter") void loadOrganisations(); }} /></div>
              <Button type="button" variant="outline" onClick={() => void loadOrganisations()}>Search</Button>
            </div>
            <div className="divide-y divide-zinc-200">
              {isLoading ? <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-500"><Loader2 className="size-4 animate-spin" /> Loading directory</div> : items.length === 0 ? <div className="flex flex-col items-center justify-center py-14 text-center"><Inbox className="size-9 text-slate-300" /><p className="mt-3 font-medium text-slate-700">No organisations found</p><p className="mt-1 text-sm text-slate-500">Create your first workspace to get started.</p></div> : items.map((organisation) => (
                <article key={organisation.id} className="flex items-center justify-between gap-4 py-4">
                  <div className="min-w-0"><p className="truncate font-medium text-slate-900">{organisation.display_name}</p><p className="mt-1 text-sm text-slate-500">{organisation.email} · <span className="capitalize">{organisation.status}</span></p></div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => router.push(`/organisations/${organisation.id}/ai-features`)}>AI Features</Button>
                    <Button size="sm" variant="outline" onClick={() => void changeStatus(organisation.id, organisation.status === "suspended" ? "activate" : "suspend")}>{organisation.status === "suspended" ? "Activate" : "Suspend"}<ChevronRight className="size-3.5" /></Button>
                    <Button size="sm" variant="outline" onClick={() => void changeStatus(organisation.id, "archive")}>Archive</Button>
                  </div>
                </article>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200/80 bg-slate-950 text-white shadow-[0_22px_60px_-32px_rgba(15,23,42,0.65)]">
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Plus className="size-5 text-emerald-300" /> Create organisation</CardTitle><p className="text-sm text-slate-400">Set up a new workspace in a few seconds.</p></CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={createOrganisation}>
              {(["name", "display_name", "email"] as const).map((field) => (
                <div className="space-y-2" key={field}><Label className="text-slate-300" htmlFor={field}>{field === "display_name" ? "Display name" : field === "name" ? "Workspace key" : "Contact email"}</Label><Input className="border-slate-700 bg-slate-900 text-white placeholder:text-slate-500" id={field} type={field === "email" ? "email" : "text"} required value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} placeholder={field === "name" ? "e.g. northstar" : field === "display_name" ? "e.g. Northstar Studio" : "team@example.com"} /></div>
              ))}
              {error ? <p role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 px-3 py-2 text-sm text-red-200">{error}</p> : null}
              {created ? <p role="status" className="flex items-center gap-2 text-sm text-emerald-300"><CheckCircle2 className="size-4" /> Organisation created successfully.</p> : null}
              <Button type="submit" disabled={isCreating} className="w-full bg-emerald-400 text-slate-950 hover:bg-emerald-300">{isCreating ? <><Loader2 className="size-4 animate-spin" /> Creating...</> : "Create organisation"}</Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}