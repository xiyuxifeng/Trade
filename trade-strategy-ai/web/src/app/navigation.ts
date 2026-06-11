import { primaryNavigation } from './route-config';
import type { NavigationItem } from './route-config';

export type NavGroup = {
  title: string;
  items: NavigationItem[];
};

export const navigationGroups: NavGroup[] = [
  {
    title: '主要功能',
    items: primaryNavigation,
  },
];

export const mainNavigation = primaryNavigation;
export const allNavigationItems = primaryNavigation;

export type NavItem = NavigationItem;
