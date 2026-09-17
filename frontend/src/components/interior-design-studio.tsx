"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, CircleDashed, ImagePlus, Loader2, Save, Sparkles, UploadCloud } from "lucide-react";

import { apiClient, ApiError } from "@/lib/api-client";

type Project = { id: string; name: string };
type Job = { id: string; status: string; output?: { version_id?: string; asset_id?: string }; error?: string | null };
type Analysis = { room_type?: string; walls?: string; floor?: string; ceiling?: string; windows?: string; doors?: string; furniture?: string; lighting?: string; colours?: string; materials?: string; architectural_elements?: string; description?: string };
type Version = { id: string; version: number; prompt: string; instructions: Record<string, string>; model?: string; saved: boolean; generated_asset_id?: string };

const analysisLabels: [keyof Analysis, string][] = [
  ["room_type", "Room type"], ["walls", "Walls"], ["floor", "Floor"], ["ceiling", "Ceiling"], ["windows", "Windows"],
  ["doors", "Doors"], ["furniture", "Furniture"], ["lighting", "Lighting"], ["colours", "Colours"], ["materials", "Materials"], ["architectural_elements", "Architecture"],
];

export function InteriorDesignStudio() {
  const [project, setProject] = useState<Project | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [originalAssetId, setOriginalAssetId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisJob, setAnalysisJob] = useState<Job | null>(null);
  const [generationJob, setGenerationJob] = useState<Job | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [prompt, setPrompt] = useState("Change this room to modern luxury style. Keep the existing architecture. Change wall colour, replace the sofa, add warm lighting, and change the flooring.");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiClient.get<Project[]>("/interior-design/project-list")
      .then((projects) => setProject(projects[0] ?? null))
      .catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Unable to load projects."));
  }, []);

  async function createProject() {
    setBusy(true); setMessage("");
    try {
      setProject(await apiClient.post<Project>("/interior-design/projects", { name: `Room study ${new Date().toLocaleDateString()}` }));
    } catch (error: unknown) {
      setMessage(error instanceof ApiError && error.status === 403
        ? "Your organisation role is read-only. Ask an organisation administrator to assign the Professional User role for Interior Design AI."
        : error instanceof Error ? error.message : "Unable to create a project.");
    } finally { setBusy(false); }
  }

  useEffect(() => {
    const job = analysisJob?.status === "QUEUED" || analysisJob?.status === "PROCESSING" ? analysisJob : generationJob?.status === "QUEUED" || generationJob?.status === "PROCESSING" ? generationJob : null;
    if (!job) return;
    const timer = window.setInterval(async () => {
      try {
        const updated = await apiClient.get<Job>(`/interior-design/jobs/${job.id}`);
        if (analysisJob?.id === updated.id) {
          setAnalysisJob(updated);
          if (updated.status === "COMPLETED") {
            const result = await apiClient.get<{ analysis: Analysis }>(`/interior-design/projects/${project?.id}/analysis`);
            setAnalysis(result.analysis);
          }
        } else {
          setGenerationJob(updated);
          if (updated.status === "COMPLETED") await refreshVersions();
        }
        if (updated.status === "COMPLETED" || updated.status === "FAILED") window.clearInterval(timer);
      } catch { setMessage("Unable to read the job status."); }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [analysisJob, generationJob, project?.id]);

  async function refreshVersions() {
    if (project) setVersions(await apiClient.get<Version[]>(`/interior-design/projects/${project.id}/versions`));
  }

  async function upload() {
    if (!project || !file) return;
    setBusy(true); setMessage("");
    try {
      const form = new FormData(); form.append("upload", file);
      const result = await apiClient.post<{ asset_id: string; analysis_job_id: string }>(`/interior-design/projects/${project.id}/original`, form, { rawBody: true });
      setOriginalAssetId(result.asset_id); setAnalysisJob({ id: result.analysis_job_id, status: "QUEUED" }); setAnalysis(null);
    } catch (error: unknown) { setMessage(error instanceof ApiError ? error.message : "Upload failed."); }
    finally { setBusy(false); }
  }

  async function generate() {
    if (!project || !originalAssetId) return;
    setBusy(true); setMessage("");
    try {
      const result = await apiClient.post<Job>(`/interior-design/projects/${project.id}/generate`, { prompt, instructions: { requested_changes: prompt }, workflow: { name: "Interior Design Image Workflow" } });
      setGenerationJob(result);
    } catch (error: unknown) { setMessage(error instanceof ApiError ? error.message : "Generation failed to queue."); }
    finally { setBusy(false); }
  }

  async function saveVersion(versionId: string) {
    await apiClient.post(`/interior-design/versions/${versionId}/save`);
    await refreshVersions();
  }

  const originalUrl = useMemo(() => originalAssetId ? `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}/interior-design/assets/${originalAssetId}` : null, [originalAssetId]);
  const latestVersion = versions[0];
  const generatedUrl = latestVersion?.generated_asset_id ? `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}/interior-design/assets/${latestVersion.generated_asset_id}` : null;

  return <main className="min-h-screen bg-[#f5f0e8] text-[#26332e]">
    <header className="border-b border-[#d9d0c2] bg-[#f8f4ee]/90 px-5 py-4 backdrop-blur md:px-10">
      <div className="mx-auto flex max-w-7xl items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.28em] text-[#aa6148]">CherukadAI / Studio</p><h1 className="mt-1 font-serif text-2xl tracking-tight md:text-3xl">Interior Design AI</h1></div><div className="flex items-center gap-2 text-xs text-[#69756f]"><CircleDashed className="size-3" /> {project ? project.name : "Opening project"}</div></div>
    </header>
    <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 md:grid-cols-[minmax(0,1.5fr)_minmax(320px,.8fr)] md:px-10">
      <section className="space-y-5">
        <div className="relative min-h-[390px] overflow-hidden border border-[#d9d0c2] bg-[#e4ddd2] shadow-[0_16px_45px_rgba(79,62,43,.08)]">
          {generatedUrl ? <img src={generatedUrl} alt="Generated interior design" className="h-full min-h-[390px] w-full object-cover" /> : originalUrl ? <img src={originalUrl} alt="Original interior" className="h-full min-h-[390px] w-full object-cover" /> : <div className="flex min-h-[390px] flex-col items-center justify-center p-8 text-center"><div className="mb-4 flex size-16 items-center justify-center rounded-full bg-[#f8f4ee] text-[#aa6148]"><ImagePlus /></div><p className="font-serif text-2xl">Start with the room.</p><p className="mt-2 max-w-sm text-sm leading-6 text-[#69756f]">Upload an architecture or interior image. The original stays untouched while every design becomes a new version.</p></div>}
          {generationJob?.status === "PROCESSING" ? <div className="absolute inset-0 flex items-center justify-center bg-[#26332e]/65 text-[#f8f4ee]"><Loader2 className="mr-2 animate-spin" /> Generating a new version</div> : null}
          {latestVersion ? <div className="absolute bottom-4 left-4 bg-[#f8f4ee]/90 px-3 py-2 text-xs uppercase tracking-[.18em] text-[#aa6148]">Version {latestVersion.version}</div> : null}
        </div>
        <div className="border border-dashed border-[#bdad9b] bg-[#faf7f2] p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-semibold">Original image</p><p className="mt-1 text-xs text-[#69756f]">JPEG, PNG, or WebP up to 25 MB</p></div>{project ? <label className="flex cursor-pointer items-center gap-2 border border-[#26332e] px-4 py-2 text-sm font-medium transition hover:bg-[#26332e] hover:text-white"><UploadCloud className="size-4" /> Choose image<input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label> : <button onClick={createProject} disabled={busy} className="flex items-center gap-2 bg-[#aa6148] px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{busy ? <Loader2 className="size-4 animate-spin" /> : <ArrowUpRight className="size-4" />} Create project</button>}</div>{file ? <div className="mt-4 flex items-center justify-between border-t border-[#e2d9cc] pt-4 text-sm"><span className="truncate pr-4">{file.name}</span><button onClick={upload} disabled={busy || !project} className="flex items-center gap-2 bg-[#aa6148] px-4 py-2 font-medium text-white disabled:opacity-50">{busy ? <Loader2 className="size-4 animate-spin" /> : <ArrowUpRight className="size-4" />} Upload & analyze</button></div> : null}</div>
      </section>
      <aside className="space-y-5">
        <div className="border border-[#d9d0c2] bg-[#faf7f2] p-5"><div className="mb-5 flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#aa6148]">01 / Read the room</p><h2 className="mt-1 font-serif text-2xl">Analysis</h2></div>{analysisJob && <span className="text-xs text-[#69756f]">{analysisJob.status}</span>}</div>{analysis ? <div className="grid grid-cols-2 gap-x-4 gap-y-4">{analysisLabels.map(([key, label]) => <div key={key}><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#aa6148]">{label}</p><p className="mt-1 text-sm leading-5 text-[#4e5d55]">{analysis[key] || "Not identified"}</p></div>)}</div> : <p className="text-sm leading-6 text-[#69756f]">Upload an image to identify the room, structure, surfaces, light, and materials.</p>}</div>
        <div className="border border-[#d9d0c2] bg-[#26332e] p-5 text-[#f8f4ee]"><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#e4a285]">02 / Direct the change</p><h2 className="mt-1 font-serif text-2xl">Design brief</h2><textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} className="mt-5 min-h-36 w-full resize-y border border-[#65736c] bg-transparent p-3 text-sm leading-6 outline-none placeholder:text-[#9ea9a2]" placeholder="Describe the design changes..." /><button onClick={generate} disabled={!originalAssetId || busy || !!(generationJob && ["QUEUED", "PROCESSING"].includes(generationJob.status))} className="mt-4 flex w-full items-center justify-center gap-2 bg-[#e4a285] px-4 py-3 text-sm font-semibold text-[#26332e] disabled:cursor-not-allowed disabled:opacity-50"><Sparkles className="size-4" /> Generate new version</button></div>
        {message ? <p className="border border-[#c77e68] bg-[#fff2ed] p-3 text-sm text-[#9e4d3a]">{message}</p> : null}
        {versions.length > 0 ? <div className="border border-[#d9d0c2] bg-[#faf7f2] p-5"><div className="mb-3 flex items-center justify-between"><h2 className="font-serif text-xl">Saved history</h2><span className="text-xs text-[#69756f]">{versions.length} versions</span></div><div className="space-y-2">{versions.map((version) => <div key={version.id} className="flex items-center justify-between border-t border-[#e2d9cc] py-3"><div><p className="text-sm font-medium">Version {version.version}</p><p className="text-xs text-[#69756f]">{version.model ?? "Configured model"}</p></div><button onClick={() => saveVersion(version.id)} disabled={version.saved} className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[#aa6148] disabled:text-[#75837b]"><Save className="size-3" /> {version.saved ? "Saved" : "Save"}</button></div>)}</div></div> : null}
      </aside>
    </div>
  </main>;
}
