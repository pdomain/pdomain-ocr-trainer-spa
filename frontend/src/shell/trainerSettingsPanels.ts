import type { SettingsPanelDescriptor } from "@pdomain/pdomain-ui/shell";
import { createElement } from "react";
import { ComputePanelContent } from "./ComputePanelContent";

/**
 * Trainer settings panels injected into the AppShell utility dock.
 * Appended after the built-in Appearance panel.
 */
export const trainerSettingsPanels: SettingsPanelDescriptor[] = [
  {
    id: "compute",
    label: "Compute",
    content: createElement(ComputePanelContent),
  },
];
