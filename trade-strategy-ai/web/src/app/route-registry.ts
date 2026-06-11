import { resolveRoute, routeConfig } from './route-config';

export type RouteKind = 'canonical' | 'compat';

export type RouteRecord = {
  label: string;
  path: string;
  description: string;
  kind: RouteKind;
};

export const routeRegistry: RouteRecord[] = routeConfig.map(({ label, path, description, kind }) => ({
  label,
  path,
  description,
  kind,
}));

export function resolveRouteByPathname(pathname: string) {
  const configured = resolveRoute(pathname);
  return routeRegistry.find((route) => route.path === configured?.path) ?? routeRegistry[0];
}
