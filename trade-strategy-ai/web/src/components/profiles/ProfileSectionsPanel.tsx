import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function formatJson(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function ProfileSectionsPanel({
  sections,
}: {
  sections: Record<string, unknown>;
}) {
  const entries = Object.entries(sections ?? {});

  if (!entries.length) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm">
        暂无配置分区。
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {entries.map(([name, value]) => (
        <Card key={name} className="border-slate-200 bg-white text-slate-900 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-3">
              <CardTitle className="text-base text-slate-900">{name}</CardTitle>
              <Badge variant="info">分区</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="max-h-72 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-800">
              {formatJson(value)}
            </pre>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
