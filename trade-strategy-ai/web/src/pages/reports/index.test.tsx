import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ReportsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import {
  downloadDailyReportHtml,
  downloadEvaluationHtml,
  getDailyReport,
  getEvaluationReport,
  listDailyReports,
  listEvaluationReports,
} from '@/lib/api/reports';

vi.mock('@/lib/api/reports', () => ({
  downloadDailyReportHtml: vi.fn(),
  downloadEvaluationHtml: vi.fn(),
  getDailyReport: vi.fn(),
  getEvaluationReport: vi.fn(),
  listDailyReports: vi.fn(),
  listEvaluationReports: vi.fn(),
}));

const mockedListDailyReports = vi.mocked(listDailyReports);
const mockedListEvaluationReports = vi.mocked(listEvaluationReports);
const mockedGetDailyReport = vi.mocked(getDailyReport);
const mockedGetEvaluationReport = vi.mocked(getEvaluationReport);
const mockedDownloadDailyReportHtml = vi.mocked(downloadDailyReportHtml);
const mockedDownloadEvaluationHtml = vi.mocked(downloadEvaluationHtml);

describe('ReportsPage', () => {
  it('renders daily and evaluation report states in the page shell', async () => {
    const user = userEvent.setup();

    mockedListDailyReports.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      reports: [
        { as_of_date: '2026-05-09', file_path: '/tmp/daily_report_2026-05-09.json', file_size: 640 },
      ],
    });
    mockedListEvaluationReports.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 50,
      reports: [],
    });
    mockedGetDailyReport.mockResolvedValue({
      status: 'success',
      report: {
        report_id: '11111111-1111-1111-1111-111111111111',
        as_of_date: '2026-05-09',
        generated_at: '2026-05-09T08:00:00Z',
        ideas: [],
        highlights: ['盘前策略已更新'],
        risks: ['成交量偏弱'],
        strategy_version_ids: ['sv-001'],
        market_universe_snapshot: { symbols: ['AAA'] },
      },
    });
    mockedGetEvaluationReport.mockResolvedValue({
      status: 'success',
      result: {
        result_id: '22222222-2222-2222-2222-222222222222',
        as_of_date: '2026-05-09',
        generated_at: '2026-05-09T15:00:00Z',
        evaluations: [],
        evidence_pack_refs: ['pack-1'],
        failure_categories: ['slippage'],
        ranking_features: { pnl: -1.2 },
        postmortem_notes: ['盘后考核确认回撤扩大'],
        summary: ['盘后考核完成'],
      },
    });
    mockedDownloadDailyReportHtml.mockResolvedValue('<h1>日报 HTML</h1>');
    mockedDownloadEvaluationHtml.mockResolvedValue('<h1>考核 HTML</h1>');

    renderWithRouter([{ path: '/reports', element: <ReportsPage /> }], ['/reports']);

    expect(await screen.findByRole('heading', { name: 'Reports center' })).toBeInTheDocument();
    await waitFor(() => {
      expect(mockedListDailyReports).toHaveBeenCalledWith(0, 50);
    });

    expect(await screen.findByText('盘前策略已更新')).toBeInTheDocument();
    expect(screen.getByText('成交量偏弱')).toBeInTheDocument();
    expect(await screen.findByTitle('HTML 预览')).toHaveAttribute('srcdoc', '<h1>日报 HTML</h1>');

    await user.click(screen.getByRole('button', { name: /盘后考核/ }));
    expect(await screen.findByText('暂无盘后考核。')).toBeInTheDocument();
  });

  it('surfaces report loading errors and keeps the page usable', async () => {
    mockedListDailyReports.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      reports: [
        { as_of_date: '2026-05-10', file_path: '/tmp/daily_report_2026-05-10.json', file_size: 512 },
      ],
    });
    mockedListEvaluationReports.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 50,
      reports: [],
    });
    mockedGetDailyReport.mockResolvedValue({
      status: 'success',
      report: {
        report_id: '33333333-3333-3333-3333-333333333333',
        as_of_date: '2026-05-10',
        generated_at: '2026-05-10T08:00:00Z',
        ideas: [],
        highlights: [],
        risks: [],
        strategy_version_ids: [],
        market_universe_snapshot: null,
      },
    });
    mockedDownloadDailyReportHtml.mockRejectedValue(new Error('daily html failed'));
    mockedGetEvaluationReport.mockResolvedValue({
      status: 'success',
      result: {
        result_id: '44444444-4444-4444-4444-444444444444',
        as_of_date: '2026-05-10',
        generated_at: '2026-05-10T15:00:00Z',
        evaluations: [],
        evidence_pack_refs: [],
        failure_categories: [],
        ranking_features: {},
        postmortem_notes: [],
        summary: [],
      },
    });
    mockedDownloadEvaluationHtml.mockResolvedValue('<h1>考核 HTML</h1>');

    renderWithRouter([{ path: '/reports', element: <ReportsPage /> }], ['/reports']);

    expect(await screen.findByText('Reports center')).toBeInTheDocument();
    expect(await screen.findByText('daily html failed')).toBeInTheDocument();
  });
});
