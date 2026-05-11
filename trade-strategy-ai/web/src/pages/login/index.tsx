import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { login } from '@/lib/api/auth';
import { setAuthToken } from '@/lib/api/http';
import type { CurrentPrincipal } from '@/types/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login({ username, password });
      setAuthToken(result.token, result.expires_at);

      // 立即写入查询缓存，避免跳转后 DashboardLayout 仍看到未认证状态
      const principal: CurrentPrincipal = {
        role: result.user.role as CurrentPrincipal['role'],
        api_key_label: result.user.display_name || result.user.username,
        authenticated: true,
        source: 'session',
      };
      queryClient.setQueryData(['auth', 'me'], principal);

      navigate('/', { replace: true });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '登录失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">TSAI</div>
          <h1>Trade Strategy AI</h1>
          <p>Web Control Console</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="login-error">
              <span>{error}</span>
            </div>
          )}

          <div className="login-field">
            <label htmlFor="username">用户名</label>
            <Input
              id="username"
              type="text"
              placeholder="请输入用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="password">密码</label>
            <Input
              id="password"
              type="password"
              placeholder="请输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <Button type="submit" disabled={loading} className="login-submit">
            {loading ? '登录中...' : '登 录'}
          </Button>
        </form>
      </div>
    </div>
  );
}
