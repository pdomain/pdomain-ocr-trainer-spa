// ProfilesPage — the profiles inventory table + create/edit/delete (spec 04 §5).

import { useEffect, useState } from "react";
import { Button, Card } from "@pdomain/pdomain-ui/primitives";
import { useProfilesStore } from "../stores/profilesStore";
import { ProfileEditDialog } from "../components/ProfileEditDialog";
import type { Profile } from "../api/profiles";

type DialogState =
  { mode: "closed" } | { mode: "create" } | { mode: "edit"; profile: Profile };

export function ProfilesPage(): React.JSX.Element {
  const profiles = useProfilesStore((s) => s.profiles);
  const hasLegacyLayout = useProfilesStore((s) => s.hasLegacyLayout);
  const loading = useProfilesStore((s) => s.loading);
  const error = useProfilesStore((s) => s.error);
  const load = useProfilesStore((s) => s.load);
  const create = useProfilesStore((s) => s.create);
  const update = useProfilesStore((s) => s.update);
  const remove = useProfilesStore((s) => s.remove);
  const migrate = useProfilesStore((s) => s.migrate);

  const [dialog, setDialog] = useState<DialogState>({ mode: "closed" });

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = async (profile: Profile) => {
    if (profile.is_base) return;
    await remove(profile.name).catch(() => undefined);
  };

  return (
    <div data-testid="profiles-page">
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Profiles</h1>
        <div>
          {hasLegacyLayout && (
            <Button
              data-testid="profiles-migrate-legacy"
              variant="ghost"
              onClick={() => void migrate()}
            >
              Migrate Legacy
            </Button>
          )}
          <Button
            data-testid="profiles-new-button"
            onClick={() => setDialog({ mode: "create" })}
          >
            New profile
          </Button>
        </div>
      </header>

      {error && (
        <p data-testid="profiles-error" role="alert">
          {error}
        </p>
      )}
      {loading && <p data-testid="profiles-loading">Loading…</p>}

      <Card>
        <table data-testid="profiles-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Display name</th>
              <th>Language</th>
              <th>Typeface</th>
              <th>Detection</th>
              <th>Recognition</th>
              <th>Typeface data</th>
              <th>Glyph</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {profiles.map((p) => (
              <tr key={p.name} data-testid={`profiles-row-${p.name}`}>
                <td>
                  <a
                    href={`/profiles/${p.name}`}
                    data-testid={`profiles-row-${p.name}-link`}
                  >
                    {p.name}
                  </a>
                </td>
                <td>{p.display_name}</td>
                <td>{p.language ?? "—"}</td>
                <td>{p.typeface ?? "—"}</td>
                <td>
                  {p.counts.detection_train_pages}/
                  {p.counts.detection_val_pages}
                </td>
                <td>
                  {p.counts.recognition_train_crops}/
                  {p.counts.recognition_val_crops}
                </td>
                <td>
                  {p.counts.typeface_train_crops}/{p.counts.typeface_val_crops}
                </td>
                <td>
                  {p.counts.glyph_train_crops}/{p.counts.glyph_val_crops}
                </td>
                <td>
                  <Button
                    data-testid={`profiles-row-${p.name}-edit`}
                    variant="ghost"
                    size="sm"
                    onClick={() => setDialog({ mode: "edit", profile: p })}
                  >
                    Edit
                  </Button>
                  <Button
                    data-testid={`profiles-row-${p.name}-delete`}
                    variant="ghost"
                    size="sm"
                    disabled={p.is_base}
                    onClick={() => void handleDelete(p)}
                  >
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {dialog.mode === "create" && (
        <ProfileEditDialog
          mode="create"
          onSubmitCreate={create}
          onClose={() => setDialog({ mode: "closed" })}
        />
      )}
      {dialog.mode === "edit" && (
        <ProfileEditDialog
          mode="edit"
          profile={dialog.profile}
          onSubmitEdit={update}
          onClose={() => setDialog({ mode: "closed" })}
        />
      )}
    </div>
  );
}
