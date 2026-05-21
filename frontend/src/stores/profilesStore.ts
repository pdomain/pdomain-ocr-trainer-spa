// Profiles store — zustand store factory holding the profile inventory
// and CRUD actions feeding ProfilesPage / ProfileEditDialog (spec 04 §5).

import { create } from "zustand";
import {
  createProfile,
  deleteProfile,
  fetchProfiles,
  migrateLegacy,
  updateProfile,
  type CreateProfilePayload,
  type Profile,
  type UpdateProfilePayload,
} from "../api/profiles";

export interface ProfilesState {
  profiles: Profile[];
  hasLegacyLayout: boolean;
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
  create: (payload: CreateProfilePayload) => Promise<void>;
  update: (name: string, payload: UpdateProfilePayload) => Promise<void>;
  remove: (name: string) => Promise<void>;
  migrate: () => Promise<void>;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export const createProfilesStore = () =>
  create<ProfilesState>((set) => {
    const refresh = async (): Promise<void> => {
      const data = await fetchProfiles();
      set({ profiles: data.profiles, hasLegacyLayout: data.has_legacy_layout });
    };

    return {
      profiles: [],
      hasLegacyLayout: false,
      loading: false,
      error: null,

      load: async () => {
        set({ loading: true, error: null });
        try {
          await refresh();
        } catch (err) {
          set({ error: errorMessage(err) });
        } finally {
          set({ loading: false });
        }
      },

      create: async (payload) => {
        set({ error: null });
        try {
          await createProfile(payload);
          await refresh();
        } catch (err) {
          set({ error: errorMessage(err) });
          throw err;
        }
      },

      update: async (name, payload) => {
        set({ error: null });
        try {
          await updateProfile(name, payload);
          await refresh();
        } catch (err) {
          set({ error: errorMessage(err) });
          throw err;
        }
      },

      remove: async (name) => {
        set({ error: null });
        try {
          await deleteProfile(name);
          await refresh();
        } catch (err) {
          set({ error: errorMessage(err) });
          throw err;
        }
      },

      migrate: async () => {
        set({ error: null });
        try {
          await migrateLegacy();
          await refresh();
        } catch (err) {
          set({ error: errorMessage(err) });
          throw err;
        }
      },
    };
  });

export const useProfilesStore = createProfilesStore();
