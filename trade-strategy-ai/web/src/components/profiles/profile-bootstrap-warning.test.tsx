import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { ProfileBootstrapWarning } from './profile-bootstrap-warning';

describe('ProfileBootstrapWarning', () => {
  it('renders a warning for the fallback default profile without snapshot', async () => {
    renderWithRouter(
      [{ path: '/', element: <ProfileBootstrapWarning profileId="default" profileSnapshotId={null} /> }],
      ['/'],
    );

    expect(await screen.findByText('当前使用的是兜底 default Profile')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '去导入正式配置' })).toBeInTheDocument();
  });

  it('does not render for a real profile or a populated default profile', async () => {
    renderWithRouter(
      [{ path: '/', element: <ProfileBootstrapWarning profileId="preview-demo" profileSnapshotId={null} /> }],
      ['/'],
    );

    expect(screen.queryByText('当前使用的是兜底 default Profile')).not.toBeInTheDocument();

    renderWithRouter(
      [{ path: '/', element: <ProfileBootstrapWarning profileId="default" profileSnapshotId="snapshot-1" /> }],
      ['/'],
    );

    expect(screen.queryByText('当前使用的是兜底 default Profile')).not.toBeInTheDocument();
  });
});
