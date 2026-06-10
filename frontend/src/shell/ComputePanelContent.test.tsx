import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createElement } from 'react';

// Stub useDeviceInfo so we can test both loading and loaded states
vi.mock('@pdomain/pdomain-ui/stores', () => ({
  useDeviceInfo: vi.fn(() => ({ loading: false, error: null, info: null,
    setDevice: vi.fn(), clearDevice: vi.fn() })),
}));
vi.mock('@pdomain/pdomain-ui/shell', () => ({
  ComputeTargetPanel: ({ info }: { info: unknown }) =>
    createElement('div', { 'data-testid': 'compute-target-panel' },
      info ? 'loaded' : 'empty'),
  createApiDeviceConfig: () => ({}),
}));

import { ComputePanelContent } from './ComputePanelContent';
import { useDeviceInfo } from '@pdomain/pdomain-ui/stores';

beforeEach(() => {
  vi.mocked(useDeviceInfo).mockReturnValue({
    loading: false, error: null, info: null,
    setDevice: vi.fn(), clearDevice: vi.fn(),
  });
});

describe('ComputePanelContent', () => {
  it('renders without crashing (no device info)', () => {
    render(createElement(ComputePanelContent));
    // No error or loading shown when info is null and no error
    expect(screen.getByTestId('compute-target-panel')).toBeTruthy();
  });

  it('renders loading message when loading and no info', () => {
    vi.mocked(useDeviceInfo).mockReturnValueOnce({
      loading: true, error: null, info: null,
      setDevice: vi.fn(), clearDevice: vi.fn(),
    });
    render(createElement(ComputePanelContent));
    expect(screen.getByText(/checking compute/i)).toBeTruthy();
  });
});
