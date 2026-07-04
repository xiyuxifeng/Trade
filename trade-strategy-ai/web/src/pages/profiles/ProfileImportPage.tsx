import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Upload } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { ApiError } from '@/lib/api/http';
import { importProfile } from '@/lib/api/profiles';
import type { ProfileImportResponse } from '@/types/profile';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '配置导入失败';
}

function MetaCard({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm text-slate-900">{value ?? '未记录'}</p>
    </div>
  );
}

function ResultPanel({ result }: { result: ProfileImportResponse | null }) {
  if (!result) {
    return <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 shadow-sm">尚未导入。</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetaCard label="配置 ID" value={result.profile.profile_id} />
        <MetaCard label="运行环境" value={result.profile.environment} />
        <MetaCard label="校验状态" value={result.profile.validation_status} />
        <MetaCard label="版本号" value={result.profile.version} />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">导入结果摘要</p>
        <p className="mt-2 text-sm text-slate-700">
          {result.created ? '已创建正式配置。' : '已更新正式配置。'}
        </p>
        <p className="mt-2 text-xs text-slate-500">
          快照：{result.snapshot?.snapshot_id ?? '无'} · {result.snapshot?.masked_sections?.length ?? 0} 个脱敏分区
        </p>
      </div>
    </div>
  );
}

export function ProfileImportPage() {
  const navigate = useNavigate();
  const [profileId, setProfileId] = useState('default');
  const [source, setSource] = useState<'app.yaml' | 'app.template.yaml'>('app.template.yaml');
  const [createdBy, setCreatedBy] = useState('web');
  const [submittedResult, setSubmittedResult] = useState<ProfileImportResponse | null>(null);

  const importMutation = useMutation({
    mutationFn: async () => {
      const trimmedProfileId = profileId.trim();
      if (!trimmedProfileId) {
        throw new Error('请输入配置 ID。');
      }
      return importProfile({
        profile_id: trimmedProfileId,
        source,
        created_by: createdBy.trim() || 'web',
      });
    },
    onSuccess: (result) => {
      setSubmittedResult(result);
    },
  });

  const submitPreview = useMemo(
    () => ({
      profile_id: profileId.trim() || '未填写',
      source,
      created_by: createdBy.trim() || 'web',
    }),
    [createdBy, profileId, source],
  );

  return (
    <main className="page-stack">
      <section className="rounded-[28px] border border-slate-200 bg-white/90 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <Badge variant="info">配置管理</Badge>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">导入为正式配置</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              选择交付模板导入一次，生成正式 Profile。导入完成后，Web 后续运行只认 Profile。
            </p>
            <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm leading-6 text-sky-900">
              <p className="font-medium text-sky-950">首次部署建议</p>
              <p className="mt-1">
                如果系统状态页仍显示 default 兜底，请先在这里导入正式配置。推荐优先使用
                <code className="rounded bg-white px-1.5 py-0.5 text-xs text-sky-900">config/app.template.yaml</code>
                ，部署环境已有的
                <code className="rounded bg-white px-1.5 py-0.5 text-xs text-sky-900">config/app.yaml</code>
                也可以作为导入源。
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => navigate('/system/configuration')}>
              返回列表
            </Button>
            <Button className="bg-sky-500 text-slate-950 hover:bg-sky-400" onClick={() => importMutation.mutate()} disabled={importMutation.isPending}>
              <Upload className="mr-2 h-4 w-4" />
              {importMutation.isPending ? '导入中' : '保存并导入'}
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
        <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">导入表单</CardTitle>
            <CardDescription className="text-slate-600">先确认输入内容，再提交导入。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700" htmlFor="profile_id">
                  配置 ID
                </label>
                <Input className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400" id="profile_id" value={profileId} onChange={(event) => setProfileId(event.target.value)} placeholder="default" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700" htmlFor="created_by">
                  创建者
                </label>
                <Input className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400" id="created_by" value={createdBy} onChange={(event) => setCreatedBy(event.target.value)} placeholder="web" />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700" htmlFor="source">
                导入模板
              </label>
              <Select
                id="source"
                className="border-slate-200 bg-white text-slate-900"
                value={source}
                onChange={(event) => setSource(event.target.value as 'app.yaml' | 'app.template.yaml')}
              >
                <option value="app.template.yaml">app.template.yaml（推荐）</option>
                <option value="app.yaml">app.yaml</option>
              </Select>
              <p className="text-xs text-slate-500">
                选择预置模板后导入，系统会把配置写入 `config_profiles`，后续 Web 只通过 Profile 串联。
              </p>
            </div>

            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-sky-700">提交前确认</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <MetaCard label="配置 ID" value={submitPreview.profile_id} />
                <MetaCard label="导入模板" value={submitPreview.source} />
                <MetaCard label="创建者" value={submitPreview.created_by} />
              </div>
              <p className="mt-3 text-xs text-sky-700">
                实际脱敏预览与校验结果由后端返回，页面不会伪造配置内容。导入成功后，后续页面只展示 Profile 和 snapshot。
              </p>
            </div>

            {importMutation.error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 shadow-sm">
                <p>{getErrorMessage(importMutation.error)}</p>
                <Button className="mt-3 border-slate-200 bg-white text-slate-700 hover:bg-slate-50" variant="outline" onClick={() => importMutation.reset()}>
                  清除错误
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white text-slate-900 shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-950">导入结果</CardTitle>
                <CardDescription className="text-slate-600">成功后可直接进入详情页继续查看。</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {importMutation.isPending ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 shadow-sm">正在提交导入请求...</div>
            ) : null}
            <ResultPanel result={submittedResult} />
            {submittedResult ? (
              <Button className="bg-sky-500 text-slate-950 hover:bg-sky-400" onClick={() => navigate(`/system/configuration/${encodeURIComponent(submittedResult.profile.profile_id)}`)}>
                进入配置详情 <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
