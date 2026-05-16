# NW-V2-S1-001 Profile Final Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Profile` the canonical long-lived config fact source, keep `config_path` only as a compatibility/import path, and ensure Job runs persist an immutable `ProfileSnapshot`.

**Architecture:** Introduce a dedicated Profile model/service boundary instead of extending the legacy `trader_profile` bundle into the new canonical system. The Profile service owns creation, import, validation, archival, and snapshot capture. `JobService` consumes a frozen snapshot at run time so later Profile edits cannot alter historical Job interpretation.

**Tech Stack:** Python, SQLAlchemy, Alembic, pytest, existing `ConfigService`, existing `ConfigSnapshotService`, existing `JobService`, existing DB session/migration layout.

---

### Task 1: Canonical Profile model, service, and migration

**Files:**
- Create: `src/models/config_profile.py`
- Modify: `src/models/__init__.py`
- Create: `src/services/config_profile_service.py`
- Modify: `src/services/__init__.py`
- Create: `src/db/migrations/versions/2026_05_16_0001_create_config_profiles_table.py`
- Create: `tests/unit/models/test_config_profile_model.py`
- Create: `tests/unit/services/test_config_profile_service.py`
- Create: `tests/unit/db/test_config_profile_migration.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_create_default_profile():
    service = ConfigProfileService()
    profile = service.create_default_profile(environment="dev", created_by="system")
    assert profile.profile_id == "default"
    assert profile.environment == "dev"
    assert profile.validation_status == "draft"
    assert profile.archived_at is None


def test_import_profile_from_config_path_masks_secrets(tmp_path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        "llm:\n  api_key: secret-1\nstorage:\n  output_dir: data/processed\n",
        encoding="utf-8",
    )
    service = ConfigProfileService()
    profile = service.import_from_config_path(config_path, profile_id="profile-dev", created_by="system")
    assert profile.profile_id == "profile-dev"
    assert profile.sections["llm"]["api_key"] == "***"
    assert profile.secret_refs["llm.api_key"] == "masked"
    assert profile.validation_status == "validated"
```

```python
def test_config_profile_migration_defines_expected_table():
    migration_file = Path(__file__).parent.parent.parent.parent / "src/db/migrations/versions/2026_05_16_0001_create_config_profiles_table.py"
    content = migration_file.read_text(encoding="utf-8")
    assert "revision = \"2026_05_16_0001\"" in content
    assert "config_profiles" in content
    assert "profile_id" in content
    assert "sections" in content
    assert "secret_refs" in content
    assert "validation_status" in content
    assert "archived_at" in content
```

- [ ] **Step 2: Run the tests to verify they fail first**

Run:

```bash
pytest tests/unit/models/test_config_profile_model.py tests/unit/services/test_config_profile_service.py tests/unit/db/test_config_profile_migration.py -v
```

Expected:

```text
ImportError or AttributeError for ConfigProfileService / ConfigProfile before implementation
```

- [ ] **Step 3: Write the minimal implementation**

```python
class ConfigProfile(Base):
    __tablename__ = "config_profiles"
    profile_id = mapped_column(String(128), primary_key=True)
    name = mapped_column(String(128), nullable=False)
    environment = mapped_column(String(64), nullable=False)
    version = mapped_column(Integer, nullable=False, default=1)
    sections = mapped_column(JSONVariant, default=dict, nullable=False)
    secret_refs = mapped_column(JSONVariant, default=dict, nullable=False)
    validation_status = mapped_column(String(32), nullable=False, default="draft")
    created_by = mapped_column(String(64), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), nullable=False)
    archived_at = mapped_column(DateTime(timezone=True))
```

```python
class ConfigProfileService(BaseService):
    def __init__(self, *, session_scope_factory: Any | None = None, snapshot_root: str | Path | None = None) -> None: ...
    def create_default_profile(self, *, environment: str, created_by: str) -> ConfigProfile: ...
    def import_from_config_path(self, config_path: str | Path, *, profile_id: str, created_by: str) -> ConfigProfile: ...
    def get_profile(self, profile_id: str) -> ConfigProfile | None: ...
    def list_profiles(self) -> list[ConfigProfile]: ...
    def update_profile(self, profile_id: str, **changes: Any) -> ConfigProfile: ...
    def archive_profile(self, profile_id: str, *, archived_by: str) -> ConfigProfile: ...
    def capture_profile_snapshot(self, profile_id: str, *, job_id: str | None = None) -> ServiceResult: ...
```

Implementation details:

- `sections` stores masked, structured profile content.
- `secret_refs` stores reference metadata only, never secret values.
- `validation_status` starts at `draft`, switches to `validated` only after import/validation succeeds.
- `create_default_profile()` creates a canonical seed profile with empty sections and no secret material.
- `import_from_config_path()` reads the existing config file through `ConfigService`, masks sensitive values, and persists the canonical Profile record.
- `capture_profile_snapshot()` writes a frozen JSON snapshot under `data/profile_snapshots/` and returns a hash/id pair that can be attached to jobs.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest tests/unit/models/test_config_profile_model.py tests/unit/services/test_config_profile_service.py tests/unit/db/test_config_profile_migration.py -v
```

Expected:

```text
passed
```

- [ ] **Step 5: Commit**

```bash
git add src/models/config_profile.py src/models/__init__.py src/services/config_profile_service.py src/services/__init__.py src/db/migrations/versions/2026_05_16_0001_create_config_profiles_table.py tests/unit/models/test_config_profile_model.py tests/unit/services/test_config_profile_service.py tests/unit/db/test_config_profile_migration.py
git commit -m "feat: add canonical profile model"
```

### Task 2: Persist immutable ProfileSnapshot in Job runs

**Files:**
- Modify: `src/services/job_service.py`
- Modify: `src/services/runtime_contracts.py`
- Create or modify: `tests/unit/services/test_job_service.py`
- Create or modify: `tests/unit/services/test_runtime_contracts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_create_job_persists_profile_snapshot(tmp_path):
    profile_service = ConfigProfileService(snapshot_root=tmp_path / "profile_snapshots")
    profile = profile_service.create_default_profile(environment="dev", created_by="system")
    job_service = JobService(config_profile_service=profile_service, job_base_dir=tmp_path / "jobs")

    created = asyncio.run(job_service.create_job(job_type="pipeline-run", params={"profile_id": profile.profile_id}, created_by="web"))

    assert created.payload["job"]["profile_snapshot"]["profile_id"] == profile.profile_id
    assert Path(created.payload["job"]["profile_snapshot_path"]).exists()
```

```python
def test_profile_snapshot_is_immutable_after_profile_change(tmp_path):
    profile_service = ConfigProfileService(snapshot_root=tmp_path / "profile_snapshots")
    profile = profile_service.create_default_profile(environment="dev", created_by="system")
    job_service = JobService(config_profile_service=profile_service, job_base_dir=tmp_path / "jobs")

    created = asyncio.run(job_service.create_job(job_type="pipeline-run", params={"profile_id": profile.profile_id}, created_by="web"))
    profile_service.update_profile(profile.profile_id, sections={"llm": {"model": "gpt-5"}})
    loaded = asyncio.run(job_service.get_job(created.payload["job"]["id"]))

    assert loaded.payload["job"]["profile_snapshot"]["sections"] == created.payload["job"]["profile_snapshot"]["sections"]
```

- [ ] **Step 2: Run the tests to verify they fail first**

Run:

```bash
pytest tests/unit/services/test_job_service.py tests/unit/services/test_runtime_contracts.py -v
```

Expected:

```text
missing profile_snapshot support / missing ProfileSnapshotRef
```

- [ ] **Step 3: Write the minimal implementation**

```python
class ProfileSnapshotRef(ContractModel):
    profile_snapshot_id: str
    profile_id: str
    profile_hash: str
    masked_sections: dict[str, Any] = Field(default_factory=dict)
    captured_at: str
```

```python
profile_snapshot_payload = None
profile_id_value = (params or {}).get("profile_id")
if profile_id_value is not None:
    snapshot_result = self._config_profile_service.capture_profile_snapshot(profile_id_value)
    if snapshot_result.status != "ok":
        return ServiceResult(status="error", message=snapshot_result.message or "profile snapshot capture failed", payload=snapshot_result.payload, warnings=snapshot_result.warnings)
    profile_snapshot_payload = snapshot_result.payload
```

Implementation details:

- `profile_id` takes precedence over `config_path` when both are present.
- `JobService` writes `profile_snapshot.json` beside `config_snapshot.json` so historical jobs remain self-contained.
- `JobService._serialize_job()` exposes `profile_snapshot` and `profile_snapshot_path` if present.
- Reloaded jobs must read the frozen snapshot from disk instead of re-hydrating from the mutable Profile table.
- `JobService.__init__()` accepts `config_profile_service: ConfigProfileService | None = None` and defaults to a new service instance when omitted.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest tests/unit/services/test_job_service.py tests/unit/services/test_runtime_contracts.py -v
```

Expected:

```text
passed
```

- [ ] **Step 5: Commit**

```bash
git add src/services/job_service.py src/services/runtime_contracts.py tests/unit/services/test_job_service.py tests/unit/services/test_runtime_contracts.py
git commit -m "feat: persist profile snapshots in jobs"
```

### Task 3: Compatibility verification and final documentation

**Files:**
- Create: `docs/New-Web-Profile-Model.md`
- Modify: `tests/unit/services/test_job_service.py`
- Modify: `tests/unit/services/test_config_profile_service.py`
- Modify: `tests/unit/db/test_config_profile_migration.py`

- [ ] **Step 1: Write the documentation and compatibility tests**

Doc content:

```md
# New Web Profile Model

## Canonical Fact Source
- Profile is the long-lived configuration fact source.
- `config_path` is compatibility-only and may be used for import/export/dev migration.

## Snapshot Rule
- Every Job run must persist a frozen Profile snapshot.
- Historical Jobs must not change when the Profile row changes later.

## Secret Handling
- Secret values are never stored in plain text.
- UI and APIs may display masked values only.
```

```python
def test_config_path_remains_compatibility_import_path(tmp_path):
    config_path = tmp_path / "app.yaml"
    config_path.write_text("storage:\n  output_dir: data/processed\n", encoding="utf-8")
    service = ConfigProfileService()
    profile = service.import_from_config_path(config_path, profile_id="profile-compat", created_by="system")
    assert profile.profile_id == "profile-compat"
    assert profile.validation_status == "validated"
```

- [ ] **Step 2: Run the focused verification suite**

Run:

```bash
pytest \
  tests/unit/models/test_config_profile_model.py \
  tests/unit/services/test_config_profile_service.py \
  tests/unit/services/test_job_service.py \
  tests/unit/services/test_runtime_contracts.py \
  tests/unit/db/test_config_profile_migration.py \
  -v
```

Expected:

```text
all pass
```

- [ ] **Step 3: Run repo-level hygiene checks**

Run:

```bash
git diff --check
```

Expected:

```text
no whitespace errors
```

- [ ] **Step 4: Commit**

```bash
git add docs/New-Web-Profile-Model.md tests/unit/services/test_job_service.py tests/unit/services/test_config_profile_service.py tests/unit/db/test_config_profile_migration.py
git commit -m "docs: record canonical profile model"
```

---

## Spec Coverage Check

- `Profile` as long-lived config fact source: Task 1
- `config_path` compatibility-only: Task 1 and Task 3
- default Profile creation: Task 1
- import from existing `config_path`: Task 1 and Task 3
- Job snapshot immutability: Task 2
- secret masking / no plain text secrets: Task 1 and Task 3
- migration coverage: Task 1
- verification and hygiene: Task 3

## Gap Check

- No gap remains for the `NW-V2-S1-001` acceptance items.
- `NW-V2-S1-002` is intentionally left out; it is a separate migration-tool task.
