import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createElement } from 'react';
import { TrainerHeader } from './TrainerHeader';

// Mock pdomain-ui shell hooks used inside TrainerHeader
vi.mock('@pdomain/pdomain-ui/shell', () => ({
  JobsPill: ({ activeJobs }: { activeJobs: unknown[] }) =>
    createElement('button', { 'data-testid': 'jobs-pill',
      'aria-label': 'Jobs' },
      `${activeJobs.length} jobs`),
  ShortcutsHelpButton: () =>
    createElement('button', { 'aria-label': 'Keyboard shortcuts' }, '?'),
  SettingsSlot: () => createElement('button', { 'aria-label': 'Settings' },
    '⚙'),
  useUtilityDock: () => ({ toggle: vi.fn() }),
}));

describe('TrainerHeader', () => {
  it('renders header-bar testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-bar')).toBeTruthy();
  });

  it('renders header-app-version testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-app-version').textContent).toContain('0.1.0');
  });

  it('renders header-help-button testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-help-button')).toBeTruthy();
  });

  it('renders header-jobs-badge testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-jobs-badge')).toBeTruthy();
  });
});
