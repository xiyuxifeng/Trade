import { NavLink } from 'react-router-dom';
import { mainNavigation } from '@/app/navigation';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/features/auth/auth-context';
import { cn } from '@/lib/utils';

type SidebarProps = {
  open?: boolean;
  mobile?: boolean;
  onNavigate?: () => void;
};

export function Sidebar({ open = true, mobile = false, onNavigate }: SidebarProps) {
  const { principal, canAccess } = useAuth();

  return (
    <aside className={cn('sidebar', mobile && 'sidebar-mobile', open && 'sidebar-open')}>
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">TSAI</div>
        <div>
          <p className="sidebar-brand-title">trade-strategy-ai</p>
          <p className="sidebar-brand-subtitle">Web control console</p>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {mainNavigation.map((item) => {
          const disabled = item.minRole ? !canAccess(item.minRole) : false;

          return (
            <NavLink
              aria-disabled={disabled || undefined}
              className={({ isActive }) =>
                cn(
                  'sidebar-link',
                  isActive && 'sidebar-link-active',
                  disabled && 'sidebar-link-disabled',
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
              <span className="sidebar-link-description">
                {disabled ? `需要 ${item.minRole} 权限` : item.description}
              </span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="flex flex-wrap items-center gap-2">
          <p>Versioned UI BFF</p>
          <Badge variant={principal.role === 'admin' ? 'success' : principal.role === 'operator' ? 'info' : 'default'}>
            {principal.role}
          </Badge>
        </div>
        <span>{principal.api_key_label ?? 'anonymous'} · /api/ui/v1/*</span>
      </div>
    </aside>
  );
}
