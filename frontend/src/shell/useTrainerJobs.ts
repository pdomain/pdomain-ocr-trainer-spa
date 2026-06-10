import { useQuery } from "@tanstack/react-query";
import type {
  ActiveJob,
  AppShellJobsProps,
  Job,
} from "@pdomain/pdomain-ui/shell";

/**
 * Raw job shape from GET /api/jobs.
 *
 * Field names MUST match the backend Job model in api/jobs.py (serialized by
 * _project() via core/models.py Job.progress).  See the producer-consumer
 * contract test in useTrainerJobs.test.ts, which uses payload copied from
 * tests/integration/api/test_jobs.py::test_list_jobs_returns_job_shape.
 */
interface RawTrainerJob {
  id: string;
  run_id: string | null;
  kind: string; // "train" | "eval" | "publish-dataset" | "publish-model"
  state: string; // "queued" | "running" | "succeeded" | "failed" | "cancelled"
  progress: number; // 0.0–1.0 (NOT "pct" — backend field name is "progress")
  error: string | null;
}

type JobStatus =
  | "queued"
  | "running"
  | "paused"
  | "succeeded"
  | "done"
  | "failed";

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
    title: j.run_id ?? j.id,
    phase: j.state,
    pct: j.progress,
    project: j.run_id ?? j.id,
  }));
  const dock: Job[] = all.map((j) => ({
    id: j.id,
    project: j.run_id ?? j.id,
    phase: j.state,
    pct: j.progress,
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
