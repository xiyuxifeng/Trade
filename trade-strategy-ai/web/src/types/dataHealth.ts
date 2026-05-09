export type DashboardReportResponse = {
  config_path: string;
  report: Record<string, unknown>;
  html_path: string | null;
  critical_alerts: number;
  exit_code: number;
};
