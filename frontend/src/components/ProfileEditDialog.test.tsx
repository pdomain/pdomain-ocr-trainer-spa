// ProfileEditDialog tests — create with metadata (scenario 3) and
// clearing a field via the edit dialog (scenario 4).

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProfileEditDialog } from "./ProfileEditDialog";
import type { Profile } from "../api/profiles";

const clogaelach: Profile = {
  name: "clogaelach",
  display_name: "clogaelach",
  language: "ga",
  typeface: "clogaelach",
  is_base: false,
  has_training_data: false,
  has_validation_data: false,
  counts: {
    detection_train_pages: 0,
    detection_val_pages: 0,
    recognition_train_crops: 0,
    recognition_val_crops: 0,
    typeface_train_crops: 0,
    typeface_val_crops: 0,
    glyph_train_crops: 0,
    glyph_val_crops: 0,
  },
};

describe("ProfileEditDialog — create mode", () => {
  it("scenario 3: submits name, language and typeface", async () => {
    const onSubmitCreate = vi.fn(() => Promise.resolve());
    render(
      <ProfileEditDialog
        mode="create"
        onSubmitCreate={onSubmitCreate}
        onClose={() => undefined}
      />,
    );
    await userEvent.type(
      screen.getByTestId("profiles-edit-dialog-name"),
      "Clogaelach",
    );
    await userEvent.type(
      screen.getByTestId("profiles-edit-dialog-language"),
      "ga",
    );
    await userEvent.selectOptions(
      screen.getByTestId("profiles-edit-dialog-typeface"),
      "clogaelach",
    );
    await userEvent.click(screen.getByTestId("profiles-edit-dialog-submit"));

    expect(onSubmitCreate).toHaveBeenCalledWith({
      name: "Clogaelach",
      display_name: null,
      language: "ga",
      typeface: "clogaelach",
    });
  });

  it("disables submit until a name is entered", () => {
    render(<ProfileEditDialog mode="create" onClose={() => undefined} />);
    expect(screen.getByTestId("profiles-edit-dialog-submit")).toBeDisabled();
  });
});

describe("ProfileEditDialog — edit mode", () => {
  it("scenario 4: clearing the typeface select submits typeface=null", async () => {
    const onSubmitEdit = vi.fn(() => Promise.resolve());
    render(
      <ProfileEditDialog
        mode="edit"
        profile={clogaelach}
        onSubmitEdit={onSubmitEdit}
        onClose={() => undefined}
      />,
    );
    await userEvent.selectOptions(
      screen.getByTestId("profiles-edit-dialog-typeface"),
      "",
    );
    await userEvent.click(screen.getByTestId("profiles-edit-dialog-submit"));

    expect(onSubmitEdit).toHaveBeenCalledWith("clogaelach", {
      display_name: "clogaelach",
      language: "ga",
      typeface: null,
    });
  });

  it("the name field is absent in edit mode", () => {
    render(
      <ProfileEditDialog
        mode="edit"
        profile={clogaelach}
        onSubmitEdit={() => Promise.resolve()}
        onClose={() => undefined}
      />,
    );
    expect(
      screen.queryByTestId("profiles-edit-dialog-name"),
    ).not.toBeInTheDocument();
  });

  it("Cancel invokes onClose", async () => {
    const onClose = vi.fn();
    render(
      <ProfileEditDialog
        mode="edit"
        profile={clogaelach}
        onSubmitEdit={() => Promise.resolve()}
        onClose={onClose}
      />,
    );
    await userEvent.click(screen.getByTestId("profiles-edit-dialog-cancel"));
    expect(onClose).toHaveBeenCalled();
  });
});
