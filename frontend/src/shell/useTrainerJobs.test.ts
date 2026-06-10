import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { useTrainerJobs } from './useTrainerJobs';

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

describe('useTrainerJobs', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 'job-1', kind: 'train', state: 'running', label: 'my-model',
            pct: 42 },
          { id: 'job-2', kind: 'eval', state: 'succeeded', label: 'my-model',
            pct: 100 },
          { id: 'job-3', kind: 'train', state: 'cancelled', label: 'x',
            pct: 0 },
        ]),
      } as Response)
    ));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('returns pill for in-flight jobs only', async () => {
    const { result } = renderHook(() => useTrainerJobs(),
      { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.pill.length).toBe(1));
    expect(result.current.pill[0].id).toBe('job-1');
  });

  it('returns all jobs in dock array', async () => {
    const { result } = renderHook(() => useTrainerJobs(),
      { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.dock.length).toBe(3));
  });

  it('maps cancelled state to failed for dock', async () => {
    const { result } = renderHook(() => useTrainerJobs(),
      { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.dock.length).toBe(3));
    const cancelled = result.current.dock.find((j) => j.id === 'job-3');
    expect(cancelled?.status).toBe('failed');
  });
});
