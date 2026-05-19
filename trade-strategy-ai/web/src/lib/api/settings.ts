import { fetchJson } from './http';
import type {
  SettingsBackupsResponse,
  SettingsConfigResponse,
  SettingsDraftRequest,
  SettingsRestoreRequest,
  SettingsRestoreResponse,
  SettingsSaveRequest,
  SettingsSaveResponse,
  SettingsSchemaResponse,
  SettingsValidationResponse,
} from '@/types/settings';

function withConfigPath(path: string, configPath?: string) {
  const params = new URLSearchParams();
  if (configPath) {
    params.set('config_path', configPath);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return `${path}${suffix}`;
}

export function getSettingsConfig(configPath?: string) {
  return fetchJson<SettingsConfigResponse>(withConfigPath('/settings/config', configPath));
}

export function getSettingsSchema(configPath?: string) {
  return fetchJson<SettingsSchemaResponse>(withConfigPath('/settings/schema', configPath));
}

export function validateSettingsDraft(request: SettingsDraftRequest) {
  return fetchJson<SettingsValidationResponse>('/settings/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function saveSettings(request: SettingsSaveRequest) {
  return fetchJson<SettingsSaveResponse>('/settings/save', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function listSettingsBackups(configPath?: string) {
  return fetchJson<SettingsBackupsResponse>(withConfigPath('/settings/backups', configPath));
}

export function restoreSettingsBackup(request: SettingsRestoreRequest) {
  return fetchJson<SettingsRestoreResponse>('/settings/restore', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
