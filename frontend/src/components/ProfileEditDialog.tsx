// ProfileEditDialog — create/edit a profile (spec 04 §5).
// pdomain-ui exports only the bare Radix Dialog root with no styled sub-parts,
// so the modal chrome here is a lightweight controlled overlay using the
// pdomain-ui Button / Input / FieldRow primitives for the form fields.

import { useEffect, useState } from "react";
import { Button, FieldRow, Input } from "@pdomain/pdomain-ui/primitives";
import {
  TYPEFACE_VALUES,
  type CreateProfilePayload,
  type Profile,
  type Typeface,
  type UpdateProfilePayload,
} from "../api/profiles";

const LANGUAGE_HINTS = ["en", "ga", "fr", "de", "la", "el", "es", "it"];

export interface ProfileEditDialogProps {
  mode: "create" | "edit";
  profile?: Profile;
  onSubmitCreate?: (payload: CreateProfilePayload) => Promise<void>;
  onSubmitEdit?: (name: string, payload: UpdateProfilePayload) => Promise<void>;
  onClose: () => void;
}

function emptyOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

export function ProfileEditDialog({
  mode,
  profile,
  onSubmitCreate,
  onSubmitEdit,
  onClose,
}: ProfileEditDialogProps): React.JSX.Element {
  const [name, setName] = useState(profile?.name ?? "");
  const [displayName, setDisplayName] = useState(profile?.display_name ?? "");
  const [language, setLanguage] = useState(profile?.language ?? "");
  const [typeface, setTypeface] = useState<string>(profile?.typeface ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "create") {
        await onSubmitCreate?.({
          name,
          display_name: emptyOrNull(displayName),
          language: emptyOrNull(language),
          typeface: (emptyOrNull(typeface) as Typeface | null) ?? null,
        });
      } else if (profile) {
        await onSubmitEdit?.(profile.name, {
          display_name: emptyOrNull(displayName),
          language: emptyOrNull(language),
          typeface: (emptyOrNull(typeface) as Typeface | null) ?? null,
        });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="profiles-edit-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={
        mode === "create" ? "New profile" : `Edit ${profile?.name ?? ""}`
      }
      style={overlayStyle}
    >
      <div style={panelStyle}>
        <h2>
          {mode === "create" ? "New profile" : `Edit ${profile?.name ?? ""}`}
        </h2>

        {mode === "create" && (
          <FieldRow>
            <label htmlFor="profile-name">Name</label>
            <Input
              id="profile-name"
              data-testid="profiles-edit-dialog-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </FieldRow>
        )}

        <FieldRow>
          <label htmlFor="profile-display-name">Display name</label>
          <Input
            id="profile-display-name"
            data-testid="profiles-edit-dialog-display-name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </FieldRow>

        <FieldRow>
          <label htmlFor="profile-language">Language</label>
          <Input
            id="profile-language"
            data-testid="profiles-edit-dialog-language"
            list="bcp47-hints"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          />
          <datalist id="bcp47-hints">
            {LANGUAGE_HINTS.map((code) => (
              <option key={code} value={code} />
            ))}
          </datalist>
        </FieldRow>

        <FieldRow>
          <label htmlFor="profile-typeface">Typeface</label>
          <select
            id="profile-typeface"
            data-testid="profiles-edit-dialog-typeface"
            value={typeface}
            onChange={(e) => setTypeface(e.target.value)}
          >
            <option value="">(unset)</option>
            {TYPEFACE_VALUES.filter((v) => v !== "typeface").map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </FieldRow>

        {error && (
          <p data-testid="profiles-edit-dialog-error" role="alert">
            {error}
          </p>
        )}

        <FieldRow>
          <Button
            data-testid="profiles-edit-dialog-cancel"
            variant="ghost"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            data-testid="profiles-edit-dialog-submit"
            onClick={() => void handleSubmit()}
            disabled={submitting || (mode === "create" && name.trim() === "")}
          >
            Save
          </Button>
        </FieldRow>
      </div>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.4)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 50,
};

const panelStyle: React.CSSProperties = {
  background: "var(--pd-surface, #fff)",
  padding: "1.5rem",
  borderRadius: "0.5rem",
  minWidth: "24rem",
};
