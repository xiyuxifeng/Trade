import { fetchJson } from './http';
import type {
  RecoveryBackupRequest,
  RecoveryBackupResponse,
  RecoveryBackupsResponse,
  RecoveryRestoreRequest,
  RecoveryRestoreResponse,
} from '@/types/ops';

export function listRecoveryBackups() {
  return fetchJson<RecoveryBackupsResponse>('/ops/backups');
}

export function createRecoveryBackup(request: RecoveryBackupRequest) {
  return fetchJson<RecoveryBackupResponse>('/ops/backup', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function restoreRecoveryBackup(request: RecoveryRestoreRequest) {
  return fetchJson<RecoveryRestoreResponse>('/ops/restore', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
