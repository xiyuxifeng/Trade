import { NavLink } from 'react-router-dom';

import { getSectionNavigation } from '@/app/route-config';
import { useAuth } from '@/features/auth/auth-context';
import { cn } from '@/lib/utils';

export function SectionNav({ parentId }: { parentId: string }) {
  const { canAccess } = useAuth();
  const items = getSectionNavigation(parentId).filter((item) => (item.minRole ? canAccess(item.minRole) : true));

  if (items.length === 0) {
    return null;
  }

  return (
    <nav aria-label="业务分区导航" className="overflow-x-auto">
      <div className="flex min-w-max gap-2 pb-1">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end
            title={item.description}
            className={({ isActive }) =>
              cn(
                'inline-flex min-w-fit items-center rounded-full border px-4 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'border-sky-500 bg-sky-500 text-white shadow-sm'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-sky-200 hover:bg-slate-50',
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
