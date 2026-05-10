export type SettingsSectionSummary = {
  key: string;
  title: string;
  summary: string;
  type: string;
  editable: boolean;
};

export type SettingsConfigResponse = {
  config_path: string;
  config: Record<string, unknown>;
  sections: SettingsSectionSummary[];
};

export type SettingsSchemaResponse = {
  config_path: string;
  sections: SettingsSectionSummary[];
};

export type SettingsValidationResponse = {
  config_path: string;
  diff: Record<string, unknown>;
  masked_config: Record<string, unknown>;
};

export type SettingsBackupItem = {
  path: string;
  name: string;
  size_bytes: number;
  modified_at: string;
};

export type SettingsBackupsResponse = {
  config_path: string;
  count: number;
  items: SettingsBackupItem[];
};

export type SettingsSaveResponse = {
  config_path: string;
  backup_path: string;
  config: Record<string, unknown>;
  reload_required?: boolean;
  reload_targets?: string[];
  restart_required?: boolean;
  restart_targets?: string[];
  reload_message?: string;
};

export type SettingsRestoreResponse = SettingsSaveResponse;

export type SettingsDraftRequest = {
  config_path: string;
  draft: Record<string, unknown>;
};

export type SettingsSaveRequest = SettingsDraftRequest & {
  confirmed: boolean;
};

export type SettingsRestoreRequest = {
  config_path: string;
  backup_path: string;
  confirmed: boolean;
};
