"use client";

import { createContext, useContext, type ReactNode } from "react";

interface FeatureGateContextValue {
  enabledFeatures: Set<string>;
}

const FeatureGateContext = createContext<FeatureGateContextValue>({
  enabledFeatures: new Set(),
});

export function FeatureGateProvider({
  enabledFeatures,
  children,
}: {
  enabledFeatures: string[];
  children: ReactNode;
}) {
  return (
    <FeatureGateContext.Provider value={{ enabledFeatures: new Set(enabledFeatures) }}>
      {children}
    </FeatureGateContext.Provider>
  );
}

/**
 * Renders `children` only when the given feature key is enabled for the current
 * organisation. This is presentation-only: the backend independently rejects
 * requests for disabled features regardless of what the UI renders.
 */
export function FeatureGate({
  feature,
  children,
  fallback = null,
}: {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { enabledFeatures } = useContext(FeatureGateContext);
  return enabledFeatures.has(feature) ? <>{children}</> : <>{fallback}</>;
}
