# Default Profile Warning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Web 的系统状态、Dashboard 和 Profile 导入页明确提示 `default` 仅是兜底运行态，引导用户导入正式 Profile，避免误用 fallback 配置。

**Architecture:** 不修改运行事实源或 API contract，仅在前端基于现有 `profile_id` / `profile_snapshot_id` 状态展示提示。复用一个小型提示组件，避免三处页面文案分叉。导入页增加静态引导，不参与运行态判断。

**Tech Stack:** React, TypeScript, React Router, Tailwind CSS, Vitest, Testing Library

---

### Task 1: Profile 兜底提示组件

**Files:**
- Create: `web/src/components/profiles/profile-bootstrap-warning.tsx`
- Test: `web/src/components/profiles/profile-bootstrap-warning.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('renders a bootstrap warning only for default profile without snapshot', async () => {
  renderWithRouter(
    [{ path: '/', element: <ProfileBootstrapWarning profileId="default" profileSnapshotId={null} /> }],
    ['/'],
  );
  expect(await screen.findByText('当前使用的是兜底 default Profile')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test -- src/components/profiles/profile-bootstrap-warning.test.tsx`
Expected: FAIL because the component does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function ProfileBootstrapWarning({ profileId, profileSnapshotId }: Props) {
  if (profileId !== 'default' || profileSnapshotId) return null;
  return (
    <div>
      <p>当前使用的是兜底 default Profile</p>
      <Button onClick={() => navigate('/profiles/import')}>去导入正式配置</Button>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test -- src/components/profiles/profile-bootstrap-warning.test.tsx`
Expected: PASS

### Task 2: 系统状态页提示

**Files:**
- Modify: `web/src/features/system-status/system-status-panel.tsx`
- Test: `web/src/features/system-status/system-status-panel.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('shows the bootstrap warning when runtime profile is default without snapshot', async () => {
  mockedUseSystemStatus.mockReturnValue({
    data: {
      status: 'ok',
      profile_id: 'default',
      profile_snapshot_id: null,
      profile_context: { profile_id: null, profile_snapshot_id: null, source: 'unset' },
      project_root: '/tmp',
      run_mode: 'web',
      database: { name: 'db', status: 'ok' },
      directories: {},
      warnings: [],
    },
    error: null,
    isLoading: false,
    isFetching: false,
    refetch: vi.fn(),
  } as never);
  expect(await screen.findByText('当前使用的是兜底 default Profile')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test -- src/features/system-status/system-status-panel.test.tsx`
Expected: FAIL until the warning is wired in.

- [ ] **Step 3: Write minimal implementation**

```tsx
<ProfileBootstrapWarning profileId={data.profile_id ?? profileContext?.profile_id} profileSnapshotId={data.profile_snapshot_id ?? profileContext?.profile_snapshot_id} />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test -- src/features/system-status/system-status-panel.test.tsx`
Expected: PASS

### Task 3: Dashboard 总览页提示

**Files:**
- Modify: `web/src/components/dashboard/dashboard-status-summary.tsx`
- Test: `web/src/components/dashboard/dashboard-status-summary.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('shows a bootstrap warning on the dashboard when only the fallback default profile exists', async () => {
  mockedUseSystemStatus.mockReturnValue({ data: { profile_id: 'default', profile_snapshot_id: null, ... }, isLoading: false, error: null, isFetching: false, refetch: vi.fn() } as never);
  expect(await screen.findByText('当前使用的是兜底 default Profile')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test -- src/components/dashboard/dashboard-status-summary.test.tsx`
Expected: FAIL until the warning is rendered.

- [ ] **Step 3: Write minimal implementation**

```tsx
<ProfileBootstrapWarning profileId={profileContext?.profile_id ?? system?.profile_id} profileSnapshotId={profileContext?.profile_snapshot_id ?? system?.profile_snapshot_id} />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test -- src/components/dashboard/dashboard-status-summary.test.tsx`
Expected: PASS

### Task 4: Profile 导入页引导文案

**Files:**
- Modify: `web/src/pages/profiles/ProfileImportPage.tsx`
- Test: `web/src/pages/profiles/ProfileImportPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
expect(await screen.findByText(/如果系统状态页仍显示 default 兜底/)).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test -- src/pages/profiles/ProfileImportPage.test.tsx`
Expected: FAIL until the guidance text is added.

- [ ] **Step 3: Write minimal implementation**

```tsx
<div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
  如果系统状态页仍显示 default 兜底，请先在这里导入正式 Profile。
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test -- src/pages/profiles/ProfileImportPage.test.tsx`
Expected: PASS

### Task 5: 文档同步

**Files:**
- Modify: `docs/web-user-manual.md`
- Modify: `docs/web-user-manual-gen2.md`
- Modify: `docs/web-deployment-operation.md`
- Modify: `docs/web-deployment-operation-gen2.md`

- [ ] **Step 1: Add the fallback warning wording**

```md
`default` 只用于系统兜底启动，不代表正式配置；如果系统状态页显示 default 且未绑定 snapshot，请先导入正式 Profile。
```

- [ ] **Step 2: Run doc diff check**

Run: `git diff --check`
Expected: PASS

---

**Coverage check**
- System status warning: Task 2
- Dashboard warning: Task 3
- Import page guidance: Task 4
- Docs: Task 5
- Shared component and test coverage: Task 1

