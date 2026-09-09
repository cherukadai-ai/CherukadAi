"use client";

import { useEffect, useState } from "react";
import { Boxes, Bot, BrainCircuit, Check, Database, Layers3, Loader2, Plus, RefreshCw, ToggleLeft } from "lucide-react";

import { ApiError, apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type RegistryItem = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  product_id?: string;
  provider?: string;
  status: string;
  version: number;
  configuration: Record<string, unknown>;
};

type Kind = "products" | "features" | "agents" | "models";
const tabs: { kind: Kind; label: string; icon: typeof Boxes }[] = [
  { kind: "products", label: "AI Products", icon: Boxes },
  { kind: "features", label: "AI Features", icon: Layers3 },
  { kind: "agents", label: "AI Agents", icon: Bot },
  { kind: "models", label: "AI Models", icon: Database },
];

export function AIRegistryAdmin() {
  const [kind, setKind] = useState<Kind>("products");
  const [items, setItems] = useState<RegistryItem[]>([]);
  const [products, setProducts] = useState<RegistryItem[]>([]);
  const [form, setForm] = useState({ code: "", name: "", description: "", product_id: "", provider: "" });
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load(target: Kind = kind) {
    setLoading(true);
    try {
      const response = await apiClient.get<{ items: RegistryItem[] }>(`/ai/${target}`);
      setItems(response.items);
      if (target === "products") setProducts(response.items);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to load registry.");
    } finally {
      setLoading(false);
    }
  }

  // Data loading is an external synchronization triggered by the selected tab.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(kind);
    if (kind !== "products" && products.length === 0) void load("products");
    // The selected tab is the only intentionally changing request dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  function selectTab(target: Kind) {
    setKind(target);
    setForm({ code: "", name: "", description: "", product_id: "", provider: "" });
    setEditing(null);
  }

  async function save() {
    setSaving(true);
    setError(null);
    const code = form.code.trim().toUpperCase();
    const name = form.name.trim();
    if (!/^[A-Z0-9_]{2,100}$/.test(code)) {
      setError("Code must be 2-100 characters using letters, numbers, or underscores.");
      setSaving(false);
      return;
    }
    if (!name) {
      setError("Name is required.");
      setSaving(false);
      return;
    }
    if (kind !== "products" && !form.product_id) {
      setError("Select a product before saving this registry item.");
      setSaving(false);
      return;
    }
    if (kind === "models" && !form.provider.trim()) {
      setError("Provider is required for models.");
      setSaving(false);
      return;
    }
    const payload = {
      code,
      name,
      description: form.description || null,
      ...(kind === "products" ? {} : { product_id: form.product_id }),
      ...(kind === "models" ? { provider: form.provider } : {}),
      configuration: {},
    };
    try {
      if (editing) await apiClient.patch(`/ai/${kind}/${editing}`, payload);
      else await apiClient.post(`/ai/${kind}/create`, payload);
      setEditing(null);
      setForm({ code: "", name: "", description: "", product_id: "", provider: "" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to save registry item.");
    } finally {
      setSaving(false);
    }
  }

  async function action(item: RegistryItem, operation: "activate" | "deactivate" | "version") {
    await apiClient.post(`/ai/${kind}/${item.id}/${operation}`);
    await load();
  }

  function edit(item: RegistryItem) {
    setEditing(item.id);
    setForm({ code: item.code, name: item.name, description: item.description ?? "", product_id: item.product_id ?? "", provider: item.provider ?? "" });
  }

  return (
    <main className="min-h-full flex-1 bg-[radial-gradient(circle_at_top_right,_#e0f2fe,_transparent_35%),linear-gradient(135deg,_#f8fafc_0%,_#eef2f5_100%)] px-5 py-7 sm:px-8 lg:px-12">
      <header className="mx-auto max-w-7xl">
        <div className="flex items-center gap-3 text-sm font-semibold uppercase tracking-[0.18em] text-sky-700"><span className="flex size-9 items-center justify-center rounded-xl bg-sky-100"><BrainCircuit className="size-4" /></span>Platform control</div>
        <div className="mt-5 flex items-end justify-between gap-4"><div><h1 className="text-4xl font-semibold tracking-tight text-slate-950">AI Registry</h1><p className="mt-2 text-slate-600">A living catalogue of products, capabilities, agents, and models.</p></div><Button variant="outline" onClick={() => void load()}><RefreshCw className="size-4" /> Refresh</Button></div>
      </header>
      <nav className="mx-auto mt-8 flex max-w-7xl gap-2 overflow-x-auto border-b border-slate-200" aria-label="AI registry sections">
        {tabs.map(({ kind: tabKind, label, icon: Icon }) => <button key={tabKind} type="button" onClick={() => selectTab(tabKind)} className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium ${kind === tabKind ? "border-sky-600 text-sky-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}><Icon className="size-4" />{label}</button>)}
      </nav>
      <section className="mx-auto mt-7 grid max-w-7xl gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Card className="border-slate-200/80 bg-white/90"><CardHeader><CardTitle>{tabs.find((tab) => tab.kind === kind)?.label} <span className="ml-2 text-sm font-normal text-slate-400">{items.length} registered</span></CardTitle></CardHeader><CardContent>{loading ? <div className="flex justify-center py-12 text-slate-500"><Loader2 className="size-5 animate-spin" /></div> : <div className="divide-y divide-slate-100">{items.map((item) => <article key={item.id} className="flex flex-wrap items-center justify-between gap-4 py-4"><div><p className="font-medium text-slate-900">{item.name}</p><p className="mt-1 text-sm text-slate-500">{item.code} · v{item.version} · <span className={item.status === "active" ? "text-emerald-700" : "text-slate-400"}>{item.status}</span></p></div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => edit(item)}>Edit</Button><Button size="sm" variant="outline" onClick={() => void action(item, item.status === "active" ? "deactivate" : "activate")}><ToggleLeft className="size-4" />{item.status === "active" ? "Deactivate" : "Activate"}</Button><Button size="sm" variant="outline" onClick={() => void action(item, "version")}>Version</Button></div></article>)}{items.length === 0 ? <p className="py-12 text-center text-sm text-slate-500">No registry items yet.</p> : null}</div>}</CardContent></Card>
        <Card className="border-sky-200/80 bg-slate-950 text-white"><CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Plus className="size-5 text-sky-300" />{editing ? "Update" : "Register"} {tabs.find((tab) => tab.kind === kind)?.label.replace("AI ", "")}</CardTitle></CardHeader><CardContent className="space-y-4"><div><Label className="text-slate-300" htmlFor="registry-code">Code</Label><Input id="registry-code" className="mt-2 border-slate-700 bg-slate-900 text-white" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} placeholder="INTERIOR_DESIGN_AI" /></div><div><Label className="text-slate-300" htmlFor="registry-name">Name</Label><Input id="registry-name" className="mt-2 border-slate-700 bg-slate-900 text-white" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></div>{kind !== "products" ? <div><Label className="text-slate-300" htmlFor="registry-product">Product</Label><select id="registry-product" className="mt-2 h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm" value={form.product_id} onChange={(event) => setForm({ ...form, product_id: event.target.value })}><option value="">Select product</option>{products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}</select></div> : null}{kind === "models" ? <div><Label className="text-slate-300" htmlFor="registry-provider">Provider</Label><Input id="registry-provider" className="mt-2 border-slate-700 bg-slate-900 text-white" value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })} /></div> : null}<div><Label className="text-slate-300" htmlFor="registry-description">Description</Label><Input id="registry-description" className="mt-2 border-slate-700 bg-slate-900 text-white" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></div>{error ? <p role="alert" className="text-sm text-red-300">{error}</p> : null}<Button className="w-full bg-sky-400 text-slate-950 hover:bg-sky-300" disabled={saving || !form.code || !form.name || (kind !== "products" && !form.product_id)} onClick={() => void save()}>{saving ? <Loader2 className="size-4 animate-spin" /> : editing ? <Check className="size-4" /> : <Plus className="size-4" />}{editing ? "Save changes" : "Register"}</Button></CardContent></Card>
      </section>
    </main>
  );
}