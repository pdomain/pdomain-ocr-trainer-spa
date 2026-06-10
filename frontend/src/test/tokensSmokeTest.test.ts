// Smoke test: ensure the CSS entry point imports pdomain-ui tokens.
// This is a static analysis check — it reads the source file, not the DOM.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";

describe("CSS entry point", () => {
  it("imports pdomain-ui tokens.css", () => {
    const css = readFileSync(resolve(__dirname, "../index.css"), "utf-8");
    expect(css).toContain("@pdomain/pdomain-ui/theme/tokens.css");
    expect(css).toContain("@pdomain/pdomain-ui/theme/primitives.css");
  });
});
