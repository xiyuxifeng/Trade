# System Management Entry Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the legacy `/admin` management center, promote `/system` into the single management entry, and expose detailed system subpages for audit, users, health, migration, backup, and restore.

**Architecture:** Keep `/system` as a compact hub page that mirrors the management-center card layout, then move each operational capability into its own canonical subpage. Reuse the existing admin/system management data-fetching and job-creation logic through focused page wrappers instead of duplicating business code. `/admin` becomes a compatibility redirect only and is removed from sidebar/navigation.

**Tech Stack:** React, React Router, TanStack Query, existing API client modules, Vitest, Testing Library.

---

### Task 1: Retire `/admin` from formal navigation and routing

**Files:**
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/components/layout/sidebar.tsx`
- Modify: `web/src/app/navigation.test.ts`
- Modify: `web/src/app/route-registry.test.ts`
- Modify: `web/src/components/layout/sidebar.test.tsx`

- [ ] **Step 1: Write the failing test**

```ts
expect(mainNavigation.map((item) => item.path)).toEqual([
  '/dashboard',
  '/jobs',
  '/workflows',
  '/articles',
  '/market',
  '/strategies',
  '/backtest',
  '/rule-pool',
  '/artifacts',
  '/profiles',
  '/system',
]);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run web/src/app/navigation.test.ts web/src/app/route-registry.test.ts web/src/components/layout/sidebar.test.tsx`
Expected: fail because `/admin` is still present.

- [ ] **Step 3: Write minimal implementation**

```ts
// navigation.ts
{
  title: '配置与管理',
  items: [{ label: '系统管理', path: '/system', description: '系统健康、审计与运维入口', minRole: 'admin' }],
}

// route-registry.ts
{ label: '系统管理', path: '/system', description: '系统健康、审计与运维入口', kind: 'canonical' },
{ label: '权限与审计', path: '/system/audit', description: '权限、审计与高风险操作历史', kind: 'canonical' },
// ... other /system subpages

// router.tsx
{ path: 'admin', element: <Navigate to="/system" replace /> },
{ path: 'admin/audit', element: <Navigate to="/system/audit" replace /> },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run web/src/app/navigation.test.ts web/src/app/route-registry.test.ts web/src/components/layout/sidebar.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/app/navigation.ts web/src/app/route-registry.ts web/src/app/router.tsx web/src/components/layout/sidebar.tsx web/src/app/navigation.test.ts web/src/app/route-registry.test.ts web/src/components/layout/sidebar.test.tsx
git commit -m "feat(web): retire admin entry from navigation"
```

### Task 2: Build `/system` as the new management hub

**Files:**
- Create: `web/src/pages/system/SystemHubPage.tsx`
- Modify: `web/src/pages/system/index.tsx`
- Modify: `web/src/pages/system/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```ts
expect(screen.getByRole('button', { name: '权限与审计' })).toBeInTheDocument();
expect(screen.getByRole('button', { name: '用户管理' })).toBeInTheDocument();
expect(screen.getByRole('button', { name: '系统健康检查' })).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run web/src/pages/system/index.test.tsx`
Expected: fail because the page still renders the old workspace shell.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function SystemHubPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="系统管理" title="系统管理" description="选择一个子功能进入详细设置。" />
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <Button onClick={() => navigate('/system/audit')}>权限与审计</Button>
          <Button onClick={() => navigate('/system/users')}>用户管理</Button>
          <Button onClick={() => navigate('/system/health')}>系统健康检查</Button>
          <Button onClick={() => navigate('/system/db-migrate')}>数据库迁移</Button>
          <Button onClick={() => navigate('/system/backup')}>数据备份</Button>
          <Button onClick={() => navigate('/system/restore')}>数据恢复</Button>
        </Card>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run web/src/pages/system/index.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/system/SystemHubPage.tsx web/src/pages/system/index.tsx web/src/pages/system/index.test.tsx
git commit -m "feat(web): add system management hub"
```

### Task 3: Split management capabilities into detail pages

**Files:**
- Create: `web/src/pages/system/AuditPage.tsx`
- Create: `web/src/pages/system/UsersPage.tsx`
- Create: `web/src/pages/system/HealthPage.tsx`
- Create: `web/src/pages/system/DatabaseMigrationPage.tsx`
- Create: `web/src/pages/system/BackupPage.tsx`
- Create: `web/src/pages/system/RestorePage.tsx`
- Modify: `web/src/features/system-management/system-management-workspace.tsx`
- Modify: `web/src/features/system-management/system-management-workspace.test.tsx`

- [ ] **Step 1: Write the failing test**

```ts
expect(await screen.findByRole('heading', { name: '用户管理' })).toBeInTheDocument();
expect(await screen.findByRole('heading', { name: '数据库迁移' })).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run web/src/features/system-management/system-management-workspace.test.tsx`
Expected: fail until the sections are exported and wrapped cleanly.

- [ ] **Step 3: Write minimal implementation**

```tsx
// export section components from system-management-workspace.tsx
export { UserManagementSection, AuditSummarySection, DatabaseMigrationSection, BackupManagementSection };

// each detail page wraps one exported section
export function UsersPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="系统管理" title="用户管理" description="添加或删除用户，修改用户权限、启用状态和密码。" />
      <UserManagementSection />
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run web/src/features/system-management/system-management-workspace.test.tsx web/src/pages/system/*.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/system/*.tsx web/src/features/system-management/system-management-workspace.tsx web/src/features/system-management/system-management-workspace.test.tsx
git commit -m "feat(web): split system management detail pages"
```

### Task 4: Update docs and task list for the new system entry

**Files:**
- Modify: `docs/New-Web-UI-Information-Architecture.md`
- Modify: `docs/New-Web-UI-Routing.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `docs/review/workflow_settings.md`

- [ ] **Step 1: Write the failing test**

```md
Search for `/admin` in formal navigation and canonical route sections.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rg -n "/admin|管理中心" docs/New-Web-UI-Information-Architecture.md docs/New-Web-UI-Routing.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md docs/review/workflow_settings.md`
Expected: matches remain before update.

- [ ] **Step 3: Write minimal implementation**

```md
- Remove `管理中心` from formal navigation.
- Keep `/admin` only as compatibility redirect text, if retained at all.
- Add `/system/audit`, `/system/users`, `/system/health`, `/system/db-migrate`, `/system/backup`, `/system/restore`.
- Update System task acceptance language to reflect hub + detail pages.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rg -n "/admin|管理中心" docs/New-Web-UI-Information-Architecture.md docs/New-Web-UI-Routing.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md docs/review/workflow_settings.md`
Expected: only compatibility mentions remain, and formal entry docs point to `/system`.

- [ ] **Step 5: Commit**

```bash
git add docs/New-Web-UI-Information-Architecture.md docs/New-Web-UI-Routing.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md docs/review/workflow_settings.md
git commit -m "docs(web): retire admin entry and expand system hub"
```

### Task 5: Verify system management flow end to end

**Files:**
- Modify: `web/src/pages/system/index.test.tsx`
- Modify: `web/src/features/system-management/system-management-workspace.test.tsx`

- [ ] **Step 1: Write the failing test**

```ts
expect(screen.getByRole('link', { name: '权限与审计' })).toHaveAttribute('href', '/system/audit');
expect(screen.getByRole('link', { name: '用户管理' })).toHaveAttribute('href', '/system/users');
expect(screen.getByRole('link', { name: '系统健康检查' })).toHaveAttribute('href', '/system/health');
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm vitest run web/src/pages/system/index.test.tsx web/src/features/system-management/system-management-workspace.test.tsx`
Expected: fail until the hub links and wrappers are wired.

- [ ] **Step 3: Write minimal implementation**

```tsx
<Button asChild>
  <Link to="/system/users">用户管理</Link>
</Button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm vitest run web/src/pages/system/index.test.tsx web/src/features/system-management/system-management-workspace.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/system/index.test.tsx web/src/features/system-management/system-management-workspace.test.tsx
git commit -m "test(web): cover system management hub flow"
```

