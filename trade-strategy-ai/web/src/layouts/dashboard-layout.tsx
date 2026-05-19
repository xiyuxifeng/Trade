import { useMemo, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { allNavigationItems } from '@/app/navigation';
import { resolveRouteByPathname } from '@/app/route-registry';
import { Sidebar } from '@/components/layout/sidebar';
import { StatusStrip } from '@/components/layout/status-strip';
import { Topbar } from '@/components/layout/topbar';
import { cn } from '@/lib/utils';
import { useAuth } from '@/features/auth/auth-context';

function resolveCurrentRoute(pathname: string) {
  const exactMatch = allNavigationItems.find((item) => item.path === pathname);
  if (exactMatch) {
    return exactMatch;
  }

  const matched = resolveRouteByPathname(pathname);
  const visibleRoute = allNavigationItems.find((item) => item.path === matched.path || item.label === matched.label);
  return visibleRoute ?? {
    label: matched.label,
    path: matched.path,
    description: matched.description,
  };
}

export function DashboardLayout() {
  const location = useLocation();
  const currentRoute = useMemo(() => resolveCurrentRoute(location.pathname), [location.pathname]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar-collapsed');
    return saved === 'true';
  });

  const handleToggleCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sidebar-collapsed', String(next));
      return next;
    });
  };

  const { principal, isLoading } = useAuth();

  // 加载中时显示空白或 loading（避免闪屏）
  if (isLoading) {
    return (
      <div className="dashboard-shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <p style={{ color: 'var(--app-muted)' }}>加载中...</p>
      </div>
    );
  }

  // 未认证（非 session 也非 API Key）→ 重定向到登录页
  if (!principal.authenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className={cn('dashboard-shell', sidebarCollapsed && 'dashboard-shell-collapsed')}>
      <div
        className={mobileNavOpen ? 'sidebar-overlay sidebar-overlay-open' : 'sidebar-overlay'}
        onClick={() => setMobileNavOpen(false)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setMobileNavOpen(false);
          }
        }}
        role="presentation"
      />

      <Sidebar mobile open={mobileNavOpen} onNavigate={() => setMobileNavOpen(false)} />
      <div className="sidebar-desktop-wrapper">
        <Sidebar collapsed={sidebarCollapsed} />
        <button
          className="sidebar-collapse-btn"
          onClick={handleToggleCollapse}
          title={sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'}
          type="button"
        >
          {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      <div className="dashboard-main">
        <Topbar
          title={currentRoute.label}
          onMenuClick={() => setMobileNavOpen((current) => !current)}
        />

        <StatusStrip
          description={currentRoute.description}
          path={currentRoute.path}
          title={currentRoute.label}
        />

        <div className="dashboard-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
