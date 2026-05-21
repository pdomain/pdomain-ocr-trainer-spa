// M0 smoke test — App renders without crashing

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders the hello page without crashing", () => {
    render(<App />);
    expect(screen.getByTestId("app-root")).toBeInTheDocument();
    expect(screen.getByText(/pd-ocr-trainer-spa/i)).toBeInTheDocument();
    expect(screen.getByText(/Hello/i)).toBeInTheDocument();
  });
});
