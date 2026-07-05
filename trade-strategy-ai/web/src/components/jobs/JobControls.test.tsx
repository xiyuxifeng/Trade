import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { JobControls } from './JobControls';

describe('JobControls', () => {
  it('shows spinner on the pending action button and disables all controls', () => {
    render(
      <JobControls
        status="running"
        canOperate
        isPending
        pendingAction="pause"
        onPause={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    const pauseButton = screen.getByRole('button', { name: '暂停中' });
    const cancelButton = screen.getByRole('button', { name: '取消' });

    expect(pauseButton).toBeDisabled();
    expect(cancelButton).toBeDisabled();
    expect(pauseButton.querySelector('.animate-spin')).not.toBeNull();
    expect(cancelButton.querySelector('.animate-spin')).toBeNull();
  });
});
