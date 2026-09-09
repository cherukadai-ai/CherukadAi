"use client";

import { useEffect, useState } from "react";
import { Check, CircleSlash, GitBranch, Loader2, Save, Send } from "lucide-react";

import { ApiError, apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Wiring = {
  id: string;
  ai_product_id: string;
  ai_feature_id: string;
  status: "enabled" | "disabled";
  configuration: Record<string, unknown>;
  version: number;
  published_at: string | null;
};

export function FeatureWiringAdmin({ organisationId }: { organisationId: string }) {
  const [items, setItems] = useState<Wiring[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const response = await apiClient.get<{ items: Wiring[] }>(`/feature-wiring/list?organisation_id=${organisationId}`);
      setItems(response.items);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to load feature wiring.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [organisationId]);

  async function action(id: string, operation: "enable" | "disable" | "publish") {
    await apiClient.post(`/feature-wiring/${id}/${operation}`);
    await load();
  }

  async function configure(item: Wiring, value: string) {
    let configuration: Record<string, unknown>;
    try { configuration = JSON.parse(value) as Record<string, unknown>; } catch { setError("Configuration must be valid JSON."); return; }
    await apiClient.patch(`/feature-wiring/${item.id}`, { configuration });
    await load();
  }

  async function rollback(item: Wiring) {
    if (item.version <= 1) return;
    await apiClient.post(`/feature-wiring/${item.id}/rollback/${item.version - 1}`);
    await load();
  }

  return (
    <main className="min-h-full flex-1 bg-[linear-gradient(135deg,_#f7fbfa_0%,_#e8f3f0_100%)] px-5 py-8 sm:px-8 lg:px-12">
      <header className="mx-auto max-w-5xl"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Organisation / AI Features</p><h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">Feature Wiring</h1><p className="mt-2 text-slate-600">Control which AI capabilities this organisation can execute.</p></header>
      <section className="mx-auto mt-8 max-w-5xl">
        <Card className="border-slate-200/80 bg-white/90 shadow-xl shadow-slate-900/5">
          <CardHeader><CardTitle>AI capability access</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {loading ? <div className="flex items-center gap-2 py-8 text-slate-500"><Loader2 className="size-4 animate-spin" /> Loading wiring</div> : items.map((item) => (
              <article key={item.id} className="grid gap-4 border-b border-slate-100 py-4 last:border-0 md:grid-cols-[1fr_auto] md:items-center">
                <div><p className="font-medium text-slate-900">Feature {item.ai_feature_id}</p><p className="mt-1 text-xs text-slate-500">Version {item.version} · {item.published_at ? "Published" : "Unpublished"}</p><Input className="mt-3 font-mono text-xs" defaultValue={JSON.stringify(item.configuration)} aria-label={`Configuration for ${item.ai_feature_id}`} onBlur={(event) => void configure(item, event.target.value)} /></div>
                <div className="flex flex-wrap gap-2"><Button size="sm" variant={item.status === "enabled" ? "default" : "outline"} onClick={() => void action(item.id, item.status === "enabled" ? "disable" : "enable")}>{item.status === "enabled" ? <Check className="size-4" /> : <CircleSlash className="size-4" />}{item.status === "enabled" ? "Enabled" : "Disabled"}</Button><Button size="sm" variant="outline" onClick={() => void action(item.id, "publish")}><Send className="size-4" /> Publish</Button><Button size="sm" variant="outline" disabled={item.version <= 1} onClick={() => void rollback(item)}><GitBranch className="size-4" /> Roll back</Button></div>
              </article>
            ))}
            {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
            {!loading && items.length === 0 ? <p className="py-8 text-sm text-slate-500">No AI features have been wired for this organisation yet.</p> : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}