import { SetupForm } from "@/app/(auth)/setup/setup-form";

export default function SetupPage() {
  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden bg-[#10231f] px-4 py-10">
      <div className="pointer-events-none absolute -left-24 top-12 h-72 w-72 rounded-full bg-[#d4a373]/20 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 bottom-0 h-96 w-96 rounded-full bg-[#6b9080]/25 blur-3xl" />
      <div className="relative z-10 w-full max-w-lg">
        <div className="mb-8 flex items-center gap-3 text-[#f6f1e9]">
          <div className="flex size-10 items-center justify-center rounded-full border border-[#d4a373]/60 bg-[#d4a373]/15 text-lg font-semibold text-[#f3cf9b]">
            C
          </div>
          <span className="text-sm font-semibold uppercase tracking-[0.24em]">CherukadAI</span>
        </div>
        <SetupForm />
      </div>
    </main>
  );
}
