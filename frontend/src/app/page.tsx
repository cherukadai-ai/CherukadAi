"use client";

import { useEffect } from "react";

import { apiClient } from "@/lib/api-client";

export default function Home() {
  useEffect(() => {
    apiClient
      .get<{ setupRequired: boolean }>("/identity/setup/status")
      .then(({ setupRequired }) => {
        window.location.replace(setupRequired ? "/setup" : "/login");
      })
      .catch(() => {
        window.location.replace("/login");
      });
  }, []);

  return (
    <div className="flex flex-1 items-center justify-center bg-[#10231f] px-6 text-center text-[#f6f1e9]">
      <p className="text-sm uppercase tracking-[0.2em] text-[#d4a373]">Loading platform</p>
    </div>
  );
}
