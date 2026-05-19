import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listUsers, createUser, updateUser, deleteUser } from '@/lib/api/auth';
import type { UserRecord } from '@/lib/api/auth';
import { useAuth } from '@/features/auth/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

type UserForm = {
  username: string;
  password: string;
  role: string;
  display_name: string;
};

const emptyForm: UserForm = { username: '', password: '', role: 'viewer', display_name: '' };

const roleOptions = [
  { value: 'viewer', label: '观察者' },
  { value: 'operator', label: '操作员' },
  { value: 'admin', label: '管理员' },
];

function roleLabel(role: string): string {
  return roleOptions.find((r) => r.value === role)?.label ?? role;
}

export function UsersPage() {
  const { canAccess } = useAuth();
  const isAdmin = canAccess('admin');
  const queryClient = useQueryClient();

  const { data: users = [], isLoading, error } = useQuery({
    queryKey: ['auth', 'users'],
    queryFn: listUsers,
    enabled: isAdmin,
  });

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<UserForm>(emptyForm);
  const [editId, setEditId] = useState<string | null>(null);
  const [formError, setFormError] = useState('');

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'users'] });
      setShowForm(false);
      setForm(emptyForm);
    },
    onError: (err: Error) => setFormError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<UserForm & { is_active: boolean }> }) =>
      updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'users'] });
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm);
    },
    onError: (err: Error) => setFormError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['auth', 'users'] }),
  });

  const handleEdit = (user: UserRecord) => {
    setEditId(user.id);
    setForm({
      username: user.username,
      password: '',
      role: user.role,
      display_name: user.display_name ?? '',
    });
    setShowForm(true);
    setFormError('');
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setFormError('');

    if (editId) {
      const data: Record<string, unknown> = {};
      if (form.password) data.password = form.password;
      if (form.role) data.role = form.role;
      data.display_name = form.display_name || null;
      updateMutation.mutate({ id: editId, data: data as Partial<UserForm & { is_active: boolean }> });
    } else {
      if (!form.username || !form.password) {
        setFormError('用户名和密码不能为空');
        return;
      }
      createMutation.mutate(form);
    }
  };

  const handleToggleActive = (user: UserRecord) => {
    updateMutation.mutate({ id: user.id, data: { is_active: !user.is_active } });
  };

  if (!isAdmin) {
    return (
      <div className="page-stack">
        <Card className="page-card">
          <p>无权访问用户管理页面</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header-copy">
          <h1>用户管理</h1>
          <p>管理系统用户、角色和权限分配</p>
        </div>
        <Button onClick={() => { setShowForm(true); setEditId(null); setForm(emptyForm); setFormError(''); }}>
          添加用户
        </Button>
      </div>

      {showForm && (
        <Card className="metric-card">
          <h3 style={{ margin: '0 0 16px' }}>{editId ? '编辑用户' : '添加新用户'}</h3>
          {formError && (
            <div style={{ color: 'var(--destructive)', marginBottom: 12, fontSize: 14 }}>{formError}</div>
          )}
          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12, maxWidth: 400 }}>
            <div>
              <label style={{ fontSize: 13, color: 'var(--app-muted)', marginBottom: 4, display: 'block' }}>用户名</label>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                disabled={!!editId}
                required={!editId}
                placeholder="登录用户名"
              />
            </div>
            <div>
              <label style={{ fontSize: 13, color: 'var(--app-muted)', marginBottom: 4, display: 'block' }}>
                {editId ? '新密码（留空不修改）' : '密码'}
              </label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required={!editId}
                minLength={6}
                placeholder={editId ? '留空则不修改密码' : '至少6位'}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, color: 'var(--app-muted)', marginBottom: 4, display: 'block' }}>显示名称</label>
              <Input
                value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                placeholder="可选的显示名称"
              />
            </div>
            <div>
              <label style={{ fontSize: 13, color: 'var(--app-muted)', marginBottom: 4, display: 'block' }}>角色</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  background: 'var(--secondary)',
                  color: 'var(--foreground)',
                  fontSize: 14,
                }}
              >
                {roleOptions.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {editId ? '保存' : '创建'}
              </Button>
              <Button type="button" variant="ghost" onClick={() => { setShowForm(false); setEditId(null); setForm(emptyForm); }}>
                取消
              </Button>
            </div>
          </form>
        </Card>
      )}

      {isLoading ? (
        <Card className="metric-card"><p>加载中...</p></Card>
      ) : error ? (
        <Card className="metric-card"><p style={{ color: 'var(--destructive)' }}>加载失败: {(error as Error).message}</p></Card>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {users.length === 0 && (
            <Card className="metric-card"><p>暂无用户</p></Card>
          )}
          {users.map((user) => (
            <Card key={user.id} className="metric-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '16px 22px' }}>
              <div style={{ display: 'grid', gap: 4, flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <strong>{user.display_name || user.username}</strong>
                  <Badge variant={user.role === 'admin' ? 'success' : user.role === 'operator' ? 'info' : 'default'}>
                    {roleLabel(user.role)}
                  </Badge>
                  {!user.is_active && (
                    <Badge variant="default" style={{ opacity: 0.6 }}>已禁用</Badge>
                  )}
                </div>
                <div style={{ fontSize: 13, color: 'var(--app-muted)' }}>
                  @{user.username}
                  {user.last_login_at && ` · 最后登录: ${new Date(user.last_login_at).toLocaleDateString('zh-CN')}`}
                  {user.created_at && ` · 创建: ${new Date(user.created_at).toLocaleDateString('zh-CN')}`}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                <Button size="sm" variant="ghost" onClick={() => handleEdit(user)}>编辑</Button>
                <Button size="sm" variant="ghost" onClick={() => handleToggleActive(user)}>
                  {user.is_active ? '禁用' : '启用'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={deleteMutation.isPending}
                  onClick={() => {
                    if (confirm(`确定删除用户 ${user.username} 吗？`)) {
                      deleteMutation.mutate(user.id);
                    }
                  }}
                  style={{ color: 'var(--destructive)' }}
                >
                  删除
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
