"""
Pattern Library Loader — 加载 YAML/JSON 格式的模式文件。

约定目录：
  data/patterns/
    canonical/        # 教科书经典形态（*.yaml）
    article/         # 文章提炼模式（*.json）
    validated/        # 验证后模式（*.json）
    library.json      # 统一模式库快照（可选）
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from src.persona.patterns import (
    ArticlePattern,
    CanonicalPattern,
    Condition,
    EvidenceRef,
    PatternLibrary,
    PatternType,
    Timeframe,
    ValidatedPattern,
    ValidationStats,
)


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parse_conditions(conds: list[dict]) -> list[Condition]:
    return [Condition(**c) for c in conds]


def _parse_evidence_refs(refs: list[dict]) -> list[EvidenceRef]:
    return [EvidenceRef(**r) for r in refs]


def _parse_validation_stats(stats: dict | None) -> ValidationStats | None:
    if not stats:
        return None
    return ValidationStats(**stats)


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------


def load_canonical_pattern(path: Path) -> CanonicalPattern:
    """Load a single canonical pattern from YAML."""
    data = load_yaml(path)
    return CanonicalPattern(
        pattern_id=data["pattern_id"],
        name_zh=data["name_zh"],
        name_en=data.get("name_en", ""),
        pattern_type=PatternType(data.get("pattern_type", "unknown")),
        timeframe=Timeframe(data.get("timeframe", "daily")),
        conditions=_parse_conditions(data.get("conditions", [])),
        entry_signal=data.get("entry_signal"),
        exit_signal=data.get("exit_signal"),
        stop_loss=data.get("stop_loss"),
        take_profit=data.get("take_profit"),
        source="canonical",
        evidence_refs=_parse_evidence_refs(data.get("evidence_refs", [])),
        description_zh=data.get("description_zh"),
        confidence=data.get("confidence"),
        book_title=data.get("book_title"),
        author=data.get("author"),
        page_ref=data.get("page_ref"),
        literature_stats=_parse_validation_stats(data.get("literature_stats")),
    )


def load_article_pattern(path: Path) -> ArticlePattern:
    """Load a single article pattern from JSON."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ArticlePattern(
        pattern_id=data["pattern_id"],
        name_zh=data["name_zh"],
        name_en=data.get("name_zh", ""),
        pattern_type=PatternType(data.get("pattern_type", "unknown")),
        timeframe=Timeframe(data.get("timeframe", "daily")),
        conditions=_parse_conditions(data.get("conditions", [])),
        entry_signal=data.get("entry_signal"),
        exit_signal=data.get("exit_signal"),
        stop_loss=data.get("stop_loss"),
        take_profit=data.get("take_profit"),
        source="article",
        evidence_refs=_parse_evidence_refs(data.get("evidence_refs", [])),
        description_zh=data.get("description_zh"),
        confidence=data.get("confidence"),
        article_ids=data.get("article_ids", []),
        extraction_method=data.get("extraction_method", "llm"),
        is_validated=data.get("is_validated", False),
        validation_stats=_parse_validation_stats(data.get("validation_stats")),
        style_cluster_id=data.get("style_cluster_id"),
    )


def load_validated_pattern(path: Path) -> ValidatedPattern:
    """Load a single validated pattern from JSON."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ValidatedPattern(
        pattern_id=data["pattern_id"],
        name_zh=data["name_zh"],
        name_en=data.get("name_en", ""),
        pattern_type=PatternType(data.get("pattern_type", "unknown")),
        timeframe=Timeframe(data.get("timeframe", "daily")),
        conditions=_parse_conditions(data.get("conditions", [])),
        entry_signal=data.get("entry_signal"),
        exit_signal=data.get("exit_signal"),
        stop_loss=data.get("stop_loss"),
        take_profit=data.get("take_profit"),
        source="validated",
        evidence_refs=_parse_evidence_refs(data.get("evidence_refs", [])),
        description_zh=data.get("description_zh"),
        confidence=data.get("confidence"),
        article_pattern_id=data.get("article_pattern_id"),
        validation_stats=ValidationStats(**data["validation_stats"]),
        validation_method=data.get("validation_method", "backtest"),
        human_confirmed=data.get("human_confirmed", False),
        confirmed_by=data.get("confirmed_by"),
    )


# ---------------------------------------------------------------------------
# Directory loaders
# ---------------------------------------------------------------------------


def load_canonical_dir(base_dir: Path) -> list[CanonicalPattern]:
    """Load all canonical patterns from data/patterns/canonical/*.yaml"""
    canonical_dir = base_dir / "data" / "patterns" / "canonical"
    if not canonical_dir.exists():
        return []

    patterns = []
    for path in sorted(canonical_dir.glob("*.yaml")):
        try:
            patterns.append(load_canonical_pattern(path))
        except Exception:  # noqa: BLE001
            # Skip malformed files
            continue
    return patterns


def load_article_dir(base_dir: Path) -> list[ArticlePattern]:
    """Load all article patterns from data/patterns/article/*.json"""
    article_dir = base_dir / "data" / "patterns" / "article"
    if not article_dir.exists():
        return []

    patterns = []
    for path in sorted(article_dir.glob("*.json")):
        try:
            patterns.append(load_article_pattern(path))
        except Exception:  # noqa: BLE001
            continue
    return patterns


def load_validated_dir(base_dir: Path) -> list[ValidatedPattern]:
    """Load all validated patterns from data/patterns/validated/*.json"""
    validated_dir = base_dir / "data" / "patterns" / "validated"
    if not validated_dir.exists():
        return []

    patterns = []
    for path in sorted(validated_dir.glob("*.json")):
        try:
            patterns.append(load_validated_pattern(path))
        except Exception:  # noqa: BLE001
            continue
    return patterns


# ---------------------------------------------------------------------------
# Full library loader
# ---------------------------------------------------------------------------


def load_pattern_library(base_dir: Path | None = None) -> PatternLibrary:
    """Load the complete pattern library from disk.

    Args:
        base_dir: Project base directory (auto-detected from env CONFIG_PATH or cwd)
    """
    if base_dir is None:
        config_path = os.environ.get("CONFIG_PATH", "config/app.yaml")
        config_path = Path(config_path)
        if config_path.parent.name == "config":
            base_dir = config_path.parent.parent
        else:
            base_dir = config_path.parent

    canonical = load_canonical_dir(base_dir)
    article = load_article_dir(base_dir)
    validated = load_validated_dir(base_dir)

    # Aggregate by type
    by_type: dict[str, int] = {}
    for p in [*canonical, *article, *validated]:
        key = p.pattern_type.value
        by_type[key] = by_type.get(key, 0) + 1

    return PatternLibrary(
        library_id="default",
        canonical_patterns=canonical,
        article_patterns=article,
        validated_patterns=validated,
        total_patterns=len(canonical) + len(article) + len(validated),
        by_type=by_type,
    )


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def save_article_pattern(base_dir: Path, pattern: ArticlePattern) -> Path:
    """Save an article pattern to JSON file."""
    article_dir = base_dir / "data" / "patterns" / "article"
    article_dir.mkdir(parents=True, exist_ok=True)
    path = article_dir / f"{pattern.pattern_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pattern.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return path


def save_validated_pattern(base_dir: Path, pattern: ValidatedPattern) -> Path:
    """Save a validated pattern to JSON file."""
    validated_dir = base_dir / "data" / "patterns" / "validated"
    validated_dir.mkdir(parents=True, exist_ok=True)
    path = validated_dir / f"{pattern.pattern_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pattern.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return path


def export_library_snapshot(base_dir: Path, library: PatternLibrary) -> Path:
    """Export the full library as a single JSON snapshot."""
    out_dir = base_dir / "data" / "patterns"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "library.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(library.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return path
