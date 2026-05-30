import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfigSnapshotPanel } from './ConfigSnapshotPanel';
import type { JobConfigSnapshot } from '@/types/jobs';

function makeSnapshot(overrides: Partial<JobConfigSnapshot> = {}): JobConfigSnapshot {
  return {
    config_snapshot_id: 'snapshot-1',
    job_id: 'job-1',
    config_path: '/Users/example/project/config/app.yaml',
    config_source: '/Users/example/project/config/app.yaml',
    config_hash: 'hash-1',
    masked_snapshot: {
      app: { api_key: '***' },
      database: { host: 'localhost' },
    },
    captured_at: '2026-05-09T07:55:00Z',
    snapshot_path: '/tmp/job-1/config_snapshot.json',
    ...overrides,
  };
}

describe('ConfigSnapshotPanel', () => {
  it('renders a read-only snapshot summary and masked sections', () => {
    render(
      <ConfigSnapshotPanel
        snapshot={makeSnapshot({
          profile_id: 'profile-1',
          validation_status: 'validated',
          masked_sections: ['app', 'database'],
        })}
      />,
    );

    expect(screen.getByText('脱敏配置快照')).toBeInTheDocument();
    expect(screen.getByText('snapshot-1')).toBeInTheDocument();
    expect(screen.getByText('profile-1')).toBeInTheDocument();
    expect(screen.getByText('validated')).toBeInTheDocument();
    expect(screen.getByText('Profile 导入来源')).toBeInTheDocument();
    expect(screen.getByText('关联 Profile')).toBeInTheDocument();
    expect(screen.getByText('app')).toBeInTheDocument();
    expect(screen.getByText('database')).toBeInTheDocument();
    expect(screen.getByText('脱敏配置快照').closest('div')?.textContent).toContain('api_key');
  });

  it('shows an empty fallback when no snapshot exists', () => {
    render(<ConfigSnapshotPanel snapshot={null} />);

    expect(screen.getByText('该任务没有配置快照。')).toBeInTheDocument();
  });

  it('shows loading and permission denied states', () => {
    const { rerender } = render(<ConfigSnapshotPanel snapshot={null} state="loading" />);
    expect(screen.getByText('正在加载配置快照...')).toBeInTheDocument();

    rerender(<ConfigSnapshotPanel snapshot={null} state="permission_denied" />);
    expect(screen.getByText('没有权限查看该配置快照。')).toBeInTheDocument();
  });

  it('shows invalid config details when validation fails', () => {
    render(
      <ConfigSnapshotPanel
        snapshot={makeSnapshot({
          validation_status: 'invalid_config',
          missing_fields: ['app.region'],
          invalid_fields: ['app.retry_count'],
        })}
        state="invalid_config"
      />,
    );

    expect(screen.getByText('配置校验未通过')).toBeInTheDocument();
    expect(screen.getByText('app.region')).toBeInTheDocument();
    expect(screen.getByText('app.retry_count')).toBeInTheDocument();
  });
});
