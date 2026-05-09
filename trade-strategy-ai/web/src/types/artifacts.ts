export type ArtifactRecord = {
  artifact_id: string;
  name: string;
  path: string;
  kind: string;
  source: string;
  exists: boolean;
  size_bytes: number | null;
  modified_at: string | null;
  previewable: boolean;
  job_id: string | null;
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
