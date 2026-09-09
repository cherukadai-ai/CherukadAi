import { describe, expect, it } from "vitest";

import { FeatureGate, FeatureGateProvider } from "@/components/feature-gate";
import { render, screen } from "@testing-library/react";

describe("FeatureGate", () => {
  it("renders children when the feature is enabled", () => {
    render(
      <FeatureGateProvider enabledFeatures={["image_analysis"]}>
        <FeatureGate feature="image_analysis">
          <span>Image Analysis</span>
        </FeatureGate>
      </FeatureGateProvider>,
    );

    expect(screen.getByText("Image Analysis")).toBeInTheDocument();
  });

  it("renders the fallback when the feature is disabled", () => {
    render(
      <FeatureGateProvider enabledFeatures={[]}>
        <FeatureGate feature="boq_ai" fallback={<span>Not available</span>}>
          <span>BOQ AI</span>
        </FeatureGate>
      </FeatureGateProvider>,
    );

    expect(screen.queryByText("BOQ AI")).not.toBeInTheDocument();
    expect(screen.getByText("Not available")).toBeInTheDocument();
  });
});
