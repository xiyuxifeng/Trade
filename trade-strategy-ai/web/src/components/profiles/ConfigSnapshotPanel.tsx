import { Badge } from '@/components/ui/badge';
import { formatTimestamp, maskAbsolutePath, stringifyJson } from '@/components/artifacts/artifact-utils';
import type { JobConfigSnapshot } from '@/types/jobs';

export type ConfigSnapshotPanelState = 'loading' | 'permission_denied' | 'invalid_config';

type ConfigSnapshotView = JobConfigSnapshot & {
  profile_id?: string | null;
  validation_status?: string | null;
  masked_sections?: string[] | null;
  missing_fields?: string[] | null;
  invalid_fields?: string[] | null;
};

type ConfigSnapshotPanelProps = {
  snapshot: ConfigSnapshotView | null;
  state?: ConfigSnapshotPanelState;
};

function SectionTitle({ children }: { children: string }) {
  return <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{children}</p>;
}

function FieldCard({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <SectionTitle>{label}</SectionTitle>
      <p className="mt-1 break-all text-sm text-slate-900">{value ?? '未提供'}</p>
    </div>
  );
}

function arrayOrFallback(values: string[] | null | undefined, fallback: string) {
  if (!values?.length) {
    return fallback;
  }
  return values.join('、');
}

function isInvalidSnapshot(snapshot: ConfigSnapshotView) {
  return (
    snapshot.validation_status === 'invalid_config' ||
    Boolean(snapshot.missing_fields?.length) ||
    Boolean(snapshot.invalid_fields?.length)
  );
}

export function ConfigSnapshotPanel({ snapshot, state }: ConfigSnapshotPanelProps) {
  if (state === 'loading') {
    return (
      <div className="space-y-3">
        <p className="text-sm text-slate-600">正在加载配置快照...</p>
        <div className="h-12 animate-pulse rounded-xl border border-slate-200 bg-white" />
        <div className="h-36 animate-pulse rounded-xl border border-slate-200 bg-white" />
      </div>
    );
  }

  if (state === 'permission_denied') {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
        没有权限查看该配置快照。
      </div>
    );
  }

  if (!snapshot) {
    return <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">该任务没有配置快照。</div>;
  }

  const invalid = state === 'invalid_config' || isInvalidSnapshot(snapshot);
  const maskedSections = snapshot.masked_sections?.length ? snapshot.masked_sections : Object.keys(snapshot.masked_snapshot || {});

  return (
    <div className="space-y-4">
      {invalid ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
          <p className="font-medium">配置校验未通过</p>
          <p className="mt-1 text-sm text-rose-50/90">该快照存在缺失或无效字段，以下信息仅用于定位问题。</p>
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        <FieldCard label="快照 ID" value={snapshot.config_snapshot_id} />
        <FieldCard label="快照来源" value={maskAbsolutePath(snapshot.config_source)} />
        <FieldCard label="快照哈希" value={snapshot.config_hash} />
        <FieldCard label="profile_id" value={snapshot.profile_id ?? '未提供'} />
        <FieldCard label="snapshot_created_at" value={formatTimestamp(snapshot.captured_at)} />
        <FieldCard label="validation_status" value={snapshot.validation_status ?? (invalid ? 'invalid_config' : '未提供')} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <SectionTitle>masked sections</SectionTitle>
          <div className="mt-2 flex flex-wrap gap-2">
            {maskedSections.length ? (
              maskedSections.map((section) => (
                <Badge key={section} variant="info">
                  {section}
                </Badge>
              ))
            ) : (
              <span className="text-sm text-slate-600">未提供</span>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <SectionTitle>missing / invalid fields</SectionTitle>
          <div className="mt-2 space-y-3 text-sm text-slate-700">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">missing fields</p>
              <p className="mt-1">{arrayOrFallback(snapshot.missing_fields, '无')}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">invalid fields</p>
              <p className="mt-1">{arrayOrFallback(snapshot.invalid_fields, '无')}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <SectionTitle>脱敏配置快照</SectionTitle>
        <p className="mt-1 text-xs text-slate-500">只展示脱敏后的内容，用于复盘和问题定位。</p>
        <pre className="mt-3 max-h-72 overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800">
          {stringifyJson(snapshot.masked_snapshot)}
        </pre>
      </div>
    </div>
  );
}
