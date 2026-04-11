"""Tests for store_db module (P1-026L)."""

from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, UTC
from uuid import uuid4

import pytest

sys.path.insert(0, "src")

from src.agents.data_agent.skills.store_db import (
    StoreStats,
    iter_jsonl,
    _parse_dt,
    _normalize_article_payload,
)


class TestIterJsonl:
    """测试 iter_jsonl 函数。"""

    def test_iter_jsonl_empty_file(self, tmp_path):
        """空文件返回空迭代器。"""
        file = tmp_path / "empty.jsonl"
        file.write_text("", encoding="utf-8")

        result = list(iter_jsonl(file))
        assert result == []

    def test_iter_jsonl_single_line(self, tmp_path):
        """单行 JSONL 正确解析。"""
        file = tmp_path / "single.jsonl"
        data = {"key": "value"}
        file.write_text(json.dumps(data) + "\n", encoding="utf-8")

        result = list(iter_jsonl(file))
        assert len(result) == 1
        assert result[0] == {"key": "value"}

    def test_iter_jsonl_multiple_lines(self, tmp_path):
        """多行 JSONL 正确解析。"""
        file = tmp_path / "multiple.jsonl"
        lines = [
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ]
        file.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")

        result = list(iter_jsonl(file))
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[2]["id"] == 3

    def test_iter_jsonl_skips_empty_lines(self, tmp_path):
        """跳过空行。"""
        file = tmp_path / "with_empty.jsonl"
        file.write_text('{"id": 1}\n\n{"id": 2}\n', encoding="utf-8")

        result = list(iter_jsonl(file))
        assert len(result) == 2

    def test_iter_jsonl_skips_whitespace_only_lines(self, tmp_path):
        """跳过只包含空白的行。"""
        file = tmp_path / "with_whitespace.jsonl"
        file.write_text('{"id": 1}\n   \n{"id": 2}\n', encoding="utf-8")

        result = list(iter_jsonl(file))
        assert len(result) == 2


class TestParseDt:
    """测试 _parse_dt 函数。"""

    def test_parse_dt_none(self):
        """None 返回 None。"""
        assert _parse_dt(None) is None

    def test_parse_dt_empty_string(self):
        """空字符串返回 None。"""
        assert _parse_dt("") is None

    def test_parse_dt_with_timezone(self):
        """带时区的日期时间正确解析。"""
        result = _parse_dt("2026-04-11T10:00:00+00:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 11

    def test_parse_dt_without_timezone(self):
        """不带时区的日期时间补上 UTC。"""
        result = _parse_dt("2026-04-11T10:00:00")
        assert result is not None
        assert result.tzinfo == UTC

    def test_parse_dt_invalid(self):
        """无效日期返回 None。"""
        assert _parse_dt("not-a-date") is None


class TestNormalizeArticlePayload:
    """测试 _normalize_article_payload 函数。"""

    def test_minimal_payload(self):
        """最小 payload 正确归一化。"""
        payload = {
            "source_url": "https://example.com/article/1",
        }
        result = _normalize_article_payload(payload)

        assert result["source"] == ""
        assert result["source_url"] == "https://example.com/article/1"
        assert result["title"] == ""
        assert result["content_text"] == ""

    def test_full_payload(self):
        """完整 payload 正确归一化。"""
        payload = {
            "source": "tgb",
            "site": "tgb.cn",
            "trader_id": "trader_a",
            "author_id": "12345",
            "author_name": "Test Author",
            "source_url": "https://tgb.cn/article/1",
            "source_article_id": "article_1",
            "title": "Test Article",
            "published_at": "2026-04-11T10:00:00",
            "crawled_at": "2026-04-11T11:00:00",
            "content_text": "Article content here",
            "content_html": "<p>Article content here</p>",
            "summary": "A test article",
            "tags": ["tag1", "tag2"],
            "content_hash": "abc123",
            "view_count": 100,
            "like_count": 10,
            "bookmark_count": 5,
            "comment_count": 20,
            "comments": [{"text": "comment1"}, {"text": "comment2"}],
            "raw_payload": {"extra": "data"},
        }
        result = _normalize_article_payload(payload)

        assert result["source"] == "tgb"
        assert result["source_url"] == "https://tgb.cn/article/1"
        assert result["title"] == "Test Article"
        assert result["content_text"] == "Article content here"
        assert result["view_count"] == 100
        assert result["like_count"] == 10
        assert result["tags"] == ["tag1", "tag2"]
        # raw_payload 应该包含原始信息和归属信息
        assert result["raw_payload"]["extra"] == "data"
        assert result["raw_payload"]["site"] == "tgb.cn"
        assert result["raw_payload"]["trader_id"] == "trader_a"
        assert result["raw_payload"]["author_id"] == "12345"

    def test_comments_payload_fallback(self):
        """使用 comments_payload 字段作为评论来源。"""
        payload = {
            "source_url": "https://example.com/article/1",
            "comments_payload": [{"text": "comment1"}],
        }
        result = _normalize_article_payload(payload)

        assert len(result["comments_payload"]) == 1

    def test_no_comments(self):
        """没有评论时返回空列表。"""
        payload = {
            "source_url": "https://example.com/article/1",
        }
        result = _normalize_article_payload(payload)

        assert result["comments_payload"] == []

    def test_invalid_comments_becomes_empty_list(self):
        """无效的评论字段返回空列表。"""
        payload = {
            "source_url": "https://example.com/article/1",
            "comments": "not-a-list",
        }
        result = _normalize_article_payload(payload)

        assert result["comments_payload"] == []

    def test_content_hash_none(self):
        """content_hash 为 None 时不报错。"""
        payload = {
            "source_url": "https://example.com/article/1",
            "content_hash": None,
        }
        result = _normalize_article_payload(payload)

        assert result["content_hash"] is None

    def test_int_fields_with_defaults(self):
        """整数字段使用默认值。"""
        payload = {
            "source_url": "https://example.com/article/1",
        }
        result = _normalize_article_payload(payload)

        assert result["view_count"] == 0
        assert result["like_count"] == 0
        assert result["bookmark_count"] == 0
        assert result["comment_count"] == 0


class TestStoreStats:
    """测试 StoreStats 数据类。"""

    def test_default_values(self):
        """默认值为 0。"""
        stats = StoreStats()

        assert stats.read_records == 0
        assert stats.inserted_articles == 0
        assert stats.updated_articles == 0
        assert stats.skipped_duplicates == 0
        assert stats.ensured_metadata == 0
        assert stats.generated_tasks == 0

    def test_custom_values(self):
        """可以设置自定义值。"""
        stats = StoreStats(
            read_records=100,
            inserted_articles=50,
            updated_articles=30,
            skipped_duplicates=20,
            ensured_metadata=50,
            generated_tasks=80,
        )

        assert stats.read_records == 100
        assert stats.inserted_articles == 50
        assert stats.updated_articles == 30
        assert stats.skipped_duplicates == 20
        assert stats.ensured_metadata == 50
        assert stats.generated_tasks == 80
