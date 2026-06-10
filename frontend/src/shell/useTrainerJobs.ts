import { useQuery } from "@tanstack/react-query";
import type { ActiveJob, AppShellJobsProps, Job } from "@pdomain/pdomain-ui/shell";

/** Raw job shape from GET /api/jobs */
interface RawTrainerJob {
  id: string;
  kind: string; // "train" | "eval" | "publish-dataset" | "publish-model"
  state: string; // "queued" | "running" | "succeeded" | "failed" | "cancelled"
  label?: string; // model name / dataset name
  pct?: number; // 0–100
}

type JobStatus = "queued" | "running" | "paused" | "succeeded" | "done" | "failed";

function toJobStatus(state: string): JobStatus {
  if (
    state === "queued" ||
    state === "running" ||
    state === "paused" ||
    state === "succeeded" ||
    state === "done" ||
    state === "failed"
  ) {
    return state;
  }
  // "cancelled" has no pdomain-ui JobStatus equivalent — map to failed
  return "failed";
}

export interface TrainerJobsResult {
  pill: ActiveJob[];
  dock: Job[];
}

/** Polls GET /api/jobs every 5 s. Returns pill (in-flight) and dock (all) shapes. */
export function useTrainerJobs(): TrainerJobsResult {
  const { data } = useQuery<RawTrainerJob[]>({
    queryKey: ["trainer-active-jobs"],
    queryFn: async () => {
      const res = await fetch("/api/jobs");
      if (!res.ok) return [];
      return (await res.json()) as RawTrainerJob[];
    },
    refetchInterval: 5_000,
    throwOnError: false,
  });
  const all = data ?? [];
  const inFlight = all.filter(
    (j) => j.state === "running" || j.state === "queued",
  );
  const pill: ActiveJob[] = inFlight.map((j) => ({
    id: j.id,
    title: j.label ?? j.id,
    phase: j.state,
    pct: j.pct ?? 0,
    project: j.label ?? j.id,
  }));
  const dock: Job[] = all.map((j) => ({
    id: j.id,
    project: j.label ?? j.id,
    phase: j.state,
    pct: j.pct ?? 0,
    status: toJobStatus(j.state),
    cancelable: false,
  }));
  return { pill, dock };
}

/** Build AppShellJobsProps from trainer jobs + navigate callback. */
export function makeJobsProps(
  dock: Job[],
  onJobOpen: AppShellJobsProps["onJobOpen"],
): AppShellJobsProps {
  return { activeJobs: dock, onJobOpen };
}
