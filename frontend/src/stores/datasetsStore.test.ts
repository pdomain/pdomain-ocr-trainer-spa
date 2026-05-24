// Datasets-kanban store tests — staged-overlay client state (spec 05 §5).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createDatasetsStore, committedColumnOf } from "./datasetsStore";
import type { KanbanView } from "../api/datasets";

function jsonResponse(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
    headers: { get: (k: string) => headers[k] ?? null },
  } as unknown as Response;
}

function view(overrides: Partial<KanbanView> = {}): KanbanView {
  return {
    profile: "all",
    task: "recognition",
    include_detection: true,
    include_recognition: true,
    columns: {
      unassigned: {
        rows: [
          {
            project_id: "myproj",
            source: "pending",
            page_count: 1,
            is_changed: false,
            style_tags: [],
            pages: [
              {
                key: "myproj:myproj_1_0.png",
                page_name: "myproj_1_0.png",
                crop_name: "myproj_1_0.png",
                label_text: "hello",
                is_changed: false,
                change_summary: null,
              },
            ],
          },
        ],
      },
      train: { rows: [] },
      val: { rows: [] },
    },
    ...overrides,
  };
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("committedColumnOf", () => {
  it("finds the committed column of a chip key", () => {
    expect(committedColumnOf(view(), "myproj:myproj_1_0.png")).toBe(
      "unassigned",
    );
    expect(committedColumnOf(view(), "ghost:x.png")).toBeUndefined();
  });
});

describe("datasetsStore", () => {
  it("load() populates the committed view and resets the overlay", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    expect(store.getState().view?.profile).toBe("all");
    expect(store.getState().staged).toEqual({});
  });

  it("stageMove() stages a chip and pendingCount reflects it", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "train");
    expect(store.getState().pendingCount()).toBe(1);
    expect(store.getState().effectiveColumnOf("myproj:myproj_1_0.png")).toBe(
      "train",
    );
  });

  it("stageMove() back to the committed column clears the staged entry", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "train");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "unassigned");
    expect(store.getState().pendingCount()).toBe(0);
  });

  it("discard() drops the staged overlay with no request", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "train");
    store.getState().discard();
    expect(store.getState().pendingCount()).toBe(0);
  });

  it("apply() POSTs the diff and replaces the view on success", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.endsWith("/apply")) {
        const committed = view({
          columns: {
            unassigned: { rows: [] },
            train: view().columns.unassigned,
            val: { rows: [] },
          },
        });
        return Promise.resolve(jsonResponse(200, committed));
      }
      return Promise.resolve(jsonResponse(200, view()));
    });
    vi.stubGlobal("fetch", fetchMock);
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "train");
    await store.getState().apply();
    const applyCall = fetchMock.mock.calls.find(([u]) =>
      String(u).endsWith("/apply"),
    );
    expect(applyCall).toBeDefined();
    const body = JSON.parse(String((applyCall?.[1] as RequestInit).body));
    expect(body.assignments).toEqual([
      { key: "myproj:myproj_1_0.png", target_split: "train" },
    ]);
    expect(store.getState().pendingCount()).toBe(0);
    expect(store.getState().statusMessage).toContain("Applied");
  });

  it("apply() surfaces X-Apply-Errors header entries", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (typeof url === "string" && url.endsWith("/apply")) {
        return Promise.resolve(
          jsonResponse(200, view(), {
            "X-Apply-Errors": JSON.stringify([
              { key: "myproj:myproj_1_0.png", error: "boom" },
            ]),
          }),
        );
      }
      return Promise.resolve(jsonResponse(200, view()));
    });
    vi.stubGlobal("fetch", fetchMock);
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "train");
    await store.getState().apply();
    expect(store.getState().applyErrors).toHaveLength(1);
  });

  it("apply() does nothing when no moves are staged", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(200, view())));
    vi.stubGlobal("fetch", fetchMock);
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    await store.getState().apply();
    expect(
      fetchMock.mock.calls.some(([u]) => String(u).endsWith("/apply")),
    ).toBe(false);
  });

  it("rescan() refreshes and discards the staged overlay", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const store = createDatasetsStore();
    await store.getState().load("all", "recognition");
    store.getState().stageMove(["myproj:myproj_1_0.png"], "train");
    await store.getState().rescan();
    expect(store.getState().pendingCount()).toBe(0);
  });
});
