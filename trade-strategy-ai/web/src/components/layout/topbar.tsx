import { LogOut, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/auth-context';

type TopbarProps = {
  title: string;
  description: string;
  onMenuClick: () => void;
};

export function Topbar({ title, description, onMenuClick }: TopbarProps) {
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
          <p className="topbar-kicker">Stage 4 dashboard shell</p>
          <h2 className="topbar-title">{title}</h2>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <p className="topbar-description">{description}</p>
        {isAuthenticated && (
          <Button variant="ghost" size="sm" onClick={handleLogoutClick} title="登出">
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
}
