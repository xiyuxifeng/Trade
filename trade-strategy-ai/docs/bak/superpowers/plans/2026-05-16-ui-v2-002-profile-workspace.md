# UI-V2-002 Profile Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V2 Profile workspace as a user-friendly, Chinese-first, light-theme management flow for list, detail, import, and read-only snapshot review.

**Architecture:** Add a thin Profile API client and typed data model first, then compose three user-facing pages around that contract: list, detail, and import, plus a read-only snapshot viewer. Keep the UI language Chinese wherever users read or act, reserve English technical tokens for backend field names and canonical object names only, and wire all new routes into the existing canonical navigation layer.

**Tech Stack:** React 18, React Router, TanStack Query, TypeScript, Vitest, Testing Library, existing shadcn/ui-style primitives.

---

### Task 1: Define Profile API contract and typed client

**Files:**
- Create: `web/src/types/profile.ts`
- Create: `web/src/lib/api/profiles.ts`
- Create: `web/src/lib/api/profiles.test.ts`

- [ ] **Step 1: Write failing tests**

  Add tests that lock the contract for:

  - `listProfiles()` issuing `GET /api/ui/v1/profiles`
  - `getProfile("default")` issuing `GET /api/ui/v1/profiles/default`
  - `importProfile()` issuing `POST /api/ui/v1/profiles/import`
  - `getProfileSnapshot("default", "snapshot-1")` issuing `GET /api/ui/v1/profiles/default/snapshots/snapshot-1`
  - unified `ApiError` mapping for JSON error payloads

  Use this exact shape in the test file:

  ```ts
  await expect(listProfiles()).resolves.toMatchObject({ items: [] });
  await expect(getProfile('default')).resolves.toMatchObject({ profile_id: 'default' });
  await expect(importProfile({ profile_id: 'default', config_path: 'config/articles.yaml' })).resolves.toMatchObject({ profile_id: 'default' });
  await expect(getProfileSnapshot('default', 'snapshot-1')).resolves.toMatchObject({ snapshot_id: 'snapshot-1' });
  ```

- [ ] **Step 2: Run the test to confirm it fails**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test -- web/src/lib/api/profiles.test.ts
  ```

  Expected: fail because the module and exported functions do not exist yet.

- [ ] **Step 3: Implement the minimal client and types**

  Add a typed `ProfileRecord`, `ProfileListResponse`, `ProfileDetailResponse`, `ProfileImportRequest`, and `ProfileSnapshotRecord` in `web/src/types/profile.ts`.

  Implement `web/src/lib/api/profiles.ts` using the existing `fetchJson()` helper from `web/src/lib/api/http.ts` and export:

  - `listProfiles()`
  - `getProfile(profileId: string)`
  - `importProfile(request: ProfileImportRequest)`
  - `getProfileSnapshot(profileId: string, snapshotId: string)`

  Keep the request/response field names aligned with the backend service model:

  - `profile_id`
  - `name`
  - `environment`
  - `version`
  - `sections`
  - `secret_refs`
  - `validation_status`
  - `created_by`
  - `updated_at`
  - `archived_at`

- [ ] **Step 4: Run the API tests again**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test -- web/src/lib/api/profiles.test.ts
  ```

  Expected: pass.

- [ ] **Step 5: Commit the contract layer**

  Commit the API client and types before building pages so the page work can consume a stable contract.

---

### Task 2: Build the Profile list, detail, and import pages

**Files:**
- Create: `web/src/pages/profiles/index.tsx`
- Create: `web/src/pages/profiles/ProfileListPage.tsx`
- Create: `web/src/pages/profiles/ProfileDetailPage.tsx`
- Create: `web/src/pages/profiles/ProfileImportPage.tsx`
- Create: `web/src/components/profiles/ProfileStatusBadge.tsx`
- Create: `web/src/components/profiles/ProfileSectionsPanel.tsx`
- Create: `web/src/components/profiles/ProfileImportForm.tsx`
- Create: `web/src/components/profiles/ProfileEmptyState.tsx`
- Create: `web/src/pages/profiles/ProfileListPage.test.tsx`
- Create: `web/src/pages/profiles/ProfileDetailPage.test.tsx`
- Create: `web/src/pages/profiles/ProfileImportPage.test.tsx`

- [ ] **Step 1: Write failing page tests**

  Write user-facing tests that assert:

  - List page shows Chinese headings, loading skeleton, empty state, error state, and retry action.
  - Detail page renders masked sections, validation status, and linked jobs summary.
  - Import page accepts `config_path`, shows masked preview text in Chinese, and blocks submit on validation errors.
  - Permission-denied state is visible and clearly labeled.

  Keep the copy in Chinese in the assertions, for example:

  ```ts
  expect(screen.getByText('Profile 列表')).toBeInTheDocument();
  expect(screen.getByText('导入为正式 Profile')).toBeInTheDocument();
  expect(screen.getByText('配置校验未通过')).toBeInTheDocument();
  ```

- [ ] **Step 2: Run the page tests to verify they fail**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test -- web/src/pages/profiles/ProfileListPage.test.tsx web/src/pages/profiles/ProfileDetailPage.test.tsx web/src/pages/profiles/ProfileImportPage.test.tsx
  ```

  Expected: fail because the page modules and components do not exist yet.

- [ ] **Step 3: Implement the pages and shared components**

  Build the pages around the new Profile API client:

  - List page: table/card hybrid with `name`, `environment`, `status`, `updated_at`, `validation_status`
  - Detail page: basic info, config sections, masked secret fields, validation result, linked jobs, and a snapshot entry point
  - Import page: `config_path` input, masked preview, validation feedback, and save confirmation

  Keep all user-visible labels Chinese, such as:

  - `Profile 列表`
  - `导入为正式 Profile`
  - `最近更新`
  - `校验状态`
  - `脱敏预览`
  - `保存为 Profile`

  Use the light-theme surface rules from the spec:

  - white / near-white backgrounds
  - low-saturation gray-blue borders
  - minimal shadows
  - strong text contrast

- [ ] **Step 4: Run the page tests again**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test -- web/src/pages/profiles/ProfileListPage.test.tsx web/src/pages/profiles/ProfileDetailPage.test.tsx web/src/pages/profiles/ProfileImportPage.test.tsx
  ```

  Expected: pass.

- [ ] **Step 5: Commit the Profile workspace pages**

  Commit the pages and shared components together so the UI shell and test surface stay aligned.

---

### Task 3: Wire routes, navigation, and snapshot deep links

**Files:**
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/pages/jobs/JobDetailPage.tsx`
- Modify: `web/src/components/profiles/ConfigSnapshotPanel.tsx`
- Create: `web/src/pages/profiles/ProfileSnapshotPage.tsx`
- Create: `web/src/pages/profiles/ProfileSnapshotPage.test.tsx`

- [ ] **Step 1: Write failing routing tests**

  Add route tests that assert:

  - `/profiles` resolves to the list page
  - `/profiles/:profileId` resolves to the detail page
  - `/profiles/import` resolves to the import page
  - `/profiles/:profileId/snapshots/:snapshotId` resolves to the snapshot page
  - the sidebar navigation shows a Chinese `Profile` entry with the right path

- [ ] **Step 2: Run the routing tests to confirm failure**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test -- web/src/app/route-registry.test.ts web/src/pages/profiles/ProfileSnapshotPage.test.tsx
  ```

  Expected: fail until routes and page exports exist.

- [ ] **Step 3: Add canonical routes and navigation entries**

  Update the router and route registry to add the new Profile routes and keep legacy compatibility untouched.

  Add a canonical main-navigation entry with Chinese copy:

  - label: `Profile`
  - description: `正式配置管理入口`
  - path: `/profiles`

  Keep legacy routes out of the main navigation.

- [ ] **Step 4: Add the snapshot deep link from Job Detail**

  Update `JobDetailPage` and `ConfigSnapshotPanel` so a user can open the linked Profile snapshot from Job Detail without seeing raw internals.

  The page should keep the current job language in Chinese and use a read-only snapshot viewer.

- [ ] **Step 5: Run routing and page tests again**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test -- web/src/app/route-registry.test.ts web/src/pages/profiles/ProfileSnapshotPage.test.tsx web/src/pages/jobs/JobDetailPage.test.tsx
  ```

  Expected: pass.

- [ ] **Step 6: Commit the route wiring**

  Commit the route and navigation wiring after verifying the deep-link path works end to end.

---

### Task 4: Polish copy, update task tracking, and verify the UI contract

**Files:**
- Modify: `web/src/pages/profiles/*`
- Modify: `web/src/components/profiles/*`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`

- [ ] **Step 1: Sweep user-facing strings to Chinese**

  Replace any newly introduced English-only UI strings with Chinese equivalents unless they are canonical identifiers or backend field names.

  Keep these technical tokens in English only when they must match the contract:

  - `Profile`
  - `Job`
  - `Snapshot`
  - `profile_id`
  - `config_path`
  - `validation_status`

- [ ] **Step 2: Run the full web validation set**

  Run:

  ```bash
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web test
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web lint
  pnpm --dir /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web typecheck
  ```

  Expected: all pass.

- [ ] **Step 3: Update TaskList status only after acceptance**

  If and only if the UI task satisfies the acceptance criteria and the new routes are working, update `UI-V2-002` in the active UI TaskList.

- [ ] **Step 4: Record the handoff context**

  Update the latest `daily-sessions` entry with:

  - current task
  - finished files
  - validation commands
  - remaining risk
  - next task number

- [ ] **Step 5: Commit the final UI package**

  Commit the UI pages, route wiring, tests, and doc updates as one coherent change set.

