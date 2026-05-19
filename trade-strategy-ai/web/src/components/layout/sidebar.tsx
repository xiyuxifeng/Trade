import { NavLink } from 'react-router-dom';
import { navigationGroups } from '@/app/navigation';
import { useAuth } from '@/features/auth/auth-context';
import { cn } from '@/lib/utils';

type SidebarProps = {
  open?: boolean;
  mobile?: boolean;
  collapsed?: boolean;
  onNavigate?: () => void;
};

export function Sidebar({ open = true, mobile = false, collapsed = false, onNavigate }: SidebarProps) {
  const { canAccess } = useAuth();

  return (
    <aside
      className={cn(
        'sidebar',
        mobile && 'sidebar-mobile',
        open && 'sidebar-open',
        collapsed && 'sidebar-collapsed',
      )}
    >
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">TSAI</div>
        {!collapsed && (
          <div>
            <p className="sidebar-brand-title">trade-strategy-ai</p>
            <p className="sidebar-brand-subtitle">Web control console</p>
          </div>
        )}
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {navigationGroups.map((group) => (
          <div key={group.title} className="sidebar-nav-group">
            {!collapsed && <p className="sidebar-nav-group-title">{group.title}</p>}
            {group.items.map((item) => {
              const disabled = item.minRole ? !canAccess(item.minRole) : false;
              const isCompatibility = group.title === '兼容入口';

              return (
                <NavLink
                  aria-disabled={disabled || undefined}
                  className={({ isActive }) =>
                    cn(
                      'sidebar-link',
                      isActive && 'sidebar-link-active',
                      disabled && 'sidebar-link-disabled',
                      collapsed && 'sidebar-link-collapsed',
                      isCompatibility && 'sidebar-link-compatibility',
                    )
                  }
                  key={item.path}
                  onClick={
                    disabled
                      ? (event) => {
                          event.preventDefault();
                        }
                      : onNavigate
                  }
                  tabIndex={disabled ? -1 : undefined}
                  to={item.path}
                  end={item.path === '/'}
                  title={disabled ? `需要 ${item.minRole} 权限` : item.description}
                >
                  <span className="sidebar-link-label">{item.label}</span>
                  {!collapsed && (
                    <span className="sidebar-link-description">
                      {disabled ? `需要 ${item.minRole} 权限` : item.description}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      {/* {!collapsed && (
        <div className="sidebar-footer">
          <div className="flex flex-wrap items-center gap-2">
            <p>Versioned UI BFF</p>
            <Badge variant={principal.role === 'admin' ? 'success' : principal.role === 'operator' ? 'info' : 'default'}>
              {principal.role}
            </Badge>
          </div>
          <span>{principal.api_key_label ?? 'anonymous'} · /api/ui/v1/*</span>
          {!principal.authenticated && (
            <NavLink to="/login" className="sidebar-link" style={{ marginTop: 8, textAlign: 'center' }}>
              <span className="sidebar-link-label">登录</span>
            </NavLink>
          )}
        </div>
      )} */}
    </aside>
  );
}
