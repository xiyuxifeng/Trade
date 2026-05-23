export type ArtifactRecord = {
  artifact_id: string;
  name: string;
  title: string;
  path?: string | null;
  kind: string;
  source: string;
  exists: boolean;
  size_bytes: number | null;
  modified_at: string | null;
  previewable: boolean;
  job_id: string | null;
  job_type: string | null;
  storage_ref: {
    source: 'file' | 'db' | 'external';
    logical_id: string;
    relative_path: string | null;
    uri: string | null;
    metadata: Record<string, unknown>;
  } | null;
  metadata: Record<string, unknown>;
  preview?: string;
  download_name?: string;
};

export type ArtifactsListResponse = {
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: ArtifactRecord[];
};

export type ArtifactFilterOptionsResponse = {
  status: string;
  kinds: string[];
  sources: string[];
  job_types: string[];
  job_ids: string[];
};
