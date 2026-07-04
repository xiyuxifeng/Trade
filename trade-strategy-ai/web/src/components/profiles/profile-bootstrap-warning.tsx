import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function isBootstrapDefaultProfile(profileId?: string | null, profileSnapshotId?: string | null) {
  return profileId === 'default' && !profileSnapshotId;
}

type ProfileBootstrapWarningProps = {
  profileId?: string | null;
  profileSnapshotId?: string | null;
  className?: string;
};

export function ProfileBootstrapWarning({ profileId, profileSnapshotId, className }: ProfileBootstrapWarningProps) {
  const navigate = useNavigate();

  if (!isBootstrapDefaultProfile(profileId, profileSnapshotId)) {
    return null;
  }

  return (
    <div
      className={cn(
        'rounded-2xl border border-amber-300 bg-amber-50/90 p-5 shadow-sm shadow-amber-950/5',
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl border border-amber-200 bg-white p-2 text-amber-700">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="warning">兜底运行态</Badge>
              <p className="text-sm font-semibold text-amber-950">当前使用的是兜底 default Profile</p>
            </div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-amber-900">
              系统为了保证 Web 能启动，自动创建了一个空白的 default Profile。它只适合调试和自愈启动，不代表你已经导入了正式配置。
            </p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-amber-900/90">
              <li>请先导入 `config/app.template.yaml` 或 `config/app.yaml` 生成正式 Profile。</li>
              <li>导入完成后，再回到系统状态页确认不再显示兜底 default。</li>
              <li>正式回测、策略构建和批量任务都应使用正式 Profile，而不是这个 fallback。</li>
            </ul>
          </div>
        </div>
        <Button
          className="border-amber-300 bg-white text-amber-900 hover:bg-amber-100"
          variant="outline"
          onClick={() => {
            navigate('/system/configuration/import');
          }}
        >
          去导入正式配置
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
