import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';

type TopbarProps = {
  title: string;
  description: string;
  onMenuClick: () => void;
};

export function Topbar({ title, description, onMenuClick }: TopbarProps) {
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

      <p className="topbar-description">{description}</p>
    </header>
  );
}
