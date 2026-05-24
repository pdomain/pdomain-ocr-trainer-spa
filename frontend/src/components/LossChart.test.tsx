// LossChart tests — empty-state + populated rendering (spec 14 §3.4).

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LossChart } from "./LossChart";

describe("LossChart", () => {
  it("renders the empty state with no series", () => {
    const { container } = render(<LossChart series={[]} />);
    expect(
      screen.getByTestId("run-detail-loss-chart-empty"),
    ).toBeInTheDocument();
    expect(container).toMatchSnapshot();
  });

  it("renders a polyline for a populated series", () => {
    render(
      <LossChart
        series={[
          { step: 1, value: 0.2 },
          { step: 2, value: 0.1 },
          { step: 3, value: 0.05 },
        ]}
        label="val_cer"
      />,
    );
    expect(screen.getByTestId("run-detail-loss-chart")).toBeInTheDocument();
    expect(
      screen.queryByTestId("run-detail-loss-chart-empty"),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/val_cer: latest 0.0500/)).toBeInTheDocument();
  });
});
