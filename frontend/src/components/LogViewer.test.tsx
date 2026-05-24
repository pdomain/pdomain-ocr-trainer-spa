// LogViewer tests — stream toggle, search filter, driver-contract testids.

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LogViewer } from "./LogViewer";

describe("LogViewer", () => {
  it("renders stdout lines with per-line testids", () => {
    render(<LogViewer stdout={["epoch 1/3", "epoch 2/3"]} stderr={[]} />);
    expect(screen.getByTestId("run-detail-log-viewer")).toBeInTheDocument();
    expect(screen.getByTestId("run-detail-log-line-0")).toHaveTextContent(
      "epoch 1/3",
    );
  });

  it("toggles to the stderr stream", async () => {
    const user = userEvent.setup();
    render(<LogViewer stdout={["out"]} stderr={["err"]} />);
    await user.click(screen.getByTestId("run-detail-log-stream-toggle"));
    expect(screen.getByTestId("run-detail-log-line-0")).toHaveTextContent(
      "err",
    );
  });

  it("filters lines by the search input", async () => {
    const user = userEvent.setup();
    render(<LogViewer stdout={["alpha", "beta", "gamma"]} stderr={[]} />);
    await user.type(screen.getByTestId("run-detail-log-search"), "bet");
    expect(screen.getByTestId("run-detail-log-line-0")).toHaveTextContent(
      "beta",
    );
    expect(screen.queryByText("alpha")).not.toBeInTheDocument();
  });
});
