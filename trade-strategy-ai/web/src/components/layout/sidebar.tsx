import { NavLink } from 'react-router-dom';
import { mainNavigation } from '@/app/navigation';
import { cn } from '@/lib/utils';

type SidebarProps = {
  open?: boolean;
  mobile?: boolean;
  onNavigate?: () => void;
};

export function Sidebar({ open = true, mobile = false, onNavigate }: SidebarProps) {
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
        {mainNavigation.map((item) => (
          <NavLink
            className={({ isActive }) =>
              cn('sidebar-link', isActive && 'sidebar-link-active')
            }
            key={item.path}
            to={item.path}
            onClick={onNavigate}
            end={item.path === '/'}
          >
            <span className="sidebar-link-label">{item.label}</span>
            <span className="sidebar-link-description">{item.description}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <p>Versioned UI BFF</p>
        <span>/api/ui/v1/*</span>
      </div>
    </aside>
  );
}
