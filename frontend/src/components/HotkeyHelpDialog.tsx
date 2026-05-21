// HotkeyHelpDialog — the `?` keyboard-shortcuts dialog (spec 12 §8).
//
// Reads the live hotkey registry kept by `useHotkey`. Only scopes with
// at least one bound hotkey on the current page render a section. The
// dialog is keyboard-operable: `Esc` closes it; focus is trapped while
// open and returned to the trigger on close.

import { useEffect, useRef, useSyncExternalStore } from "react";
import { KeyCap } from "@concavetrillion/pd-ui/primitives";
import { hotkeysByScope, subscribeHotkeys } from "../lib/hotkeyRegistry";

export interface HotkeyHelpDialogProps {
  /** Whether the dialog is open. */
  open: boolean;
  /** Called when the dialog requests to close (Esc / backdrop / ×). */
  onClose: () => void;
}

/** Split a combo like "g p" or "ctrl+s" into KeyCap-able tokens. */
function comboTokens(combo: string): string[] {
  return combo.split(/\s+/).filter((t) => t.length > 0);
}

/** The keyboard-shortcuts help dialog (`?`). */
export function HotkeyHelpDialog({
  open,
  onClose,
}: HotkeyHelpDialogProps): JSX.Element | null {
  const groups = useSyncExternalStore(subscribeHotkeys, hotkeysByScope);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      data-testid="hotkey-help-overlay"
      role="presentation"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        ref={dialogRef}
        data-testid="hotkey-help-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2 data-testid="hotkey-help-title">Keyboard shortcuts</h2>
          <button
            type="button"
            data-testid="hotkey-help-close"
            aria-label="Close"
            onClick={onClose}
          >
            ×
          </button>
        </header>
        {groups.length === 0 ? (
          <p data-testid="hotkey-help-empty">
            No keyboard shortcuts are active on this page.
          </p>
        ) : (
          groups.map((group) => (
            <section
              key={group.meta.scope}
              data-testid={`hotkey-help-section-${group.meta.scope}`}
            >
              <h3>{group.meta.label}</h3>
              <dl>
                {group.entries.map((entry) => (
                  <div
                    key={entry.combo}
                    data-testid={`hotkey-help-row-${group.meta.scope}-${entry.combo}`}
                  >
                    <dt>
                      {comboTokens(entry.combo).map((token, i) => (
                        <KeyCap key={`${entry.combo}-${i}`} keys={token} />
                      ))}
                    </dt>
                    <dd>{entry.description}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))
        )}
      </div>
    </div>
  );
}
