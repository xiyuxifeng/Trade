import { useLocation } from 'react-router-dom';
import { PlaceholderPage } from '@/components/layout/placeholder-page';

export function LegacyCompatibilityPage() {
  const location = useLocation();

  return (
    <PlaceholderPage
      description="旧入口兼容层，仅用于历史书签和过渡链接。"
      note={`当前路径 ${location.pathname} 是兼容入口，请切换到 canonical 路由。`}
      title="Legacy Compatibility"
    />
  );
}
