import { useMemo, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { mainNavigation } from '@/app/navigation';
import { Sidebar } from '@/components/layout/sidebar';
import { StatusStrip } from '@/components/layout/status-strip';
import { Topbar } from '@/components/layout/topbar';

function resolveCurrentRoute(pathname: string) {
  return (
    mainNavigation.find((item) => item.path === pathname) ??
    mainNavigation[0] ?? {
      label: 'Overview',
      path: '/',
      description: 'System health and entry summary',
    }
  );
}

export function DashboardLayout() {
  const location = useLocation();
  const currentRoute = useMemo(() => resolveCurrentRoute(location.pathname), [location.pathname]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="dashboard-shell">
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
      <Sidebar />

      <div className="dashboard-main">
        <Topbar
          title={currentRoute.label}
          description={currentRoute.description}
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
