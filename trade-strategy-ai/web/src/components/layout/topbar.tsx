import { LogOut, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/features/auth/auth-context';

type TopbarProps = {
  title: string;
  onMenuClick: () => void;
};

export function Topbar({ title, onMenuClick }: TopbarProps) {
  const { principal, isAuthenticated, handleLogout } = useAuth();
  const navigate = useNavigate();

  const handleLogoutClick = () => {
    handleLogout();
    navigate('/login');
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <Button className="topbar-menu-button" variant="ghost" onClick={onMenuClick} size="sm">
          <Menu className="h-4 w-4" />
          Menu
        </Button>
        <div>
          <h2 className="topbar-title">{title}</h2>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isAuthenticated && (
          <>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>{principal.username || principal.api_key_label || principal.source}</span>
              <Badge variant={principal.role === 'admin' ? 'success' : principal.role === 'operator' ? 'info' : 'default'}>
                {principal.role}
              </Badge>
            </span>
            <Button variant="ghost" size="sm" onClick={handleLogoutClick} title="登出">
              <LogOut className="h-4 w-4" />
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
