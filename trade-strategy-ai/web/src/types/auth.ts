export type PrincipalRole = 'anonymous' | 'viewer' | 'operator' | 'admin';

export type CurrentPrincipal = {
  role: PrincipalRole;
  api_key_label: string | null;
  authenticated: boolean;
  source: string;
  username: string;
};
