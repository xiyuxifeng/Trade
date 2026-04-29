"""NTL-S7-011: notes 字段截断测试"""
import pytest
from src.backtest.engine import _truncate_notes


class TestTruncateNotes:
    """notes 字段截断逻辑测试"""

    def test_notes_within_limit_returns_unchanged(self):
        """notes 总大小在 1KB 以内时，保持不变"""
        notes = ["normal note", "another note"]
        result = _truncate_notes(notes, max_size=1024)
        assert result == ["normal note", "another note"]

    def test_notes_exceeds_limit_truncates_from_end(self):
        """notes 超过 1KB 时，从后往前删直到合适大小"""
        # 创建一个会超过 1KB 的 notes
        long_note = "x" * 2000  # 2000 bytes
        notes = ["short note", long_note, "another short note"]

        result = _truncate_notes(notes, max_size=1024)

        # 应该保留 "short note"，删除后面的直到大小合适
        total_size = sum(len(n.encode("utf-8")) for n in result)
        assert total_size <= 1024
        assert result[0] == "short note"
        assert "[notes truncated due to size limit]" in result

    def test_truncated_notes_preserves_marker(self):
        """截断后的 notes 包含截断标记"""
        very_long_note = "y" * 3000
        notes = [very_long_note]

        result = _truncate_notes(notes, max_size=1024)

        assert "[notes truncated due to size limit]" in result
        # 至少保留了截断标记
        assert len(result) >= 1

    def test_single_note_exceeds_limit_is_replaced_with_marker(self):
        """只有一个超长 note 时，替换为截断标记"""
        very_long_note = "z" * 2000
        notes = [very_long_note]

        result = _truncate_notes(notes, max_size=1024)

        assert len(result) == 1
        assert result[0] == "[notes truncated due to size limit]"

    def test_empty_notes_returns_empty(self):
        """空 notes 返回空列表"""
        result = _truncate_notes([], max_size=1024)
        assert result == []

    def test_exactly_1kb_notes_returns_unchanged(self):
        """刚好 1KB 的 notes 保持不变（边界情况）"""
        notes = ["a" * 1024]
        result = _truncate_notes(notes, max_size=1024)
        assert result == ["a" * 1024]

    def test_hit_symbols_long_string_truncated(self):
        """hit_symbols 长字符串被正确截断"""
        # 模拟一个很长的 hit_symbols（超过 1024 字节）
        hit_symbols = ",".join([f"2026-04-{i:02d}:000001.SZ" for i in range(1, 50)])  # 加长到 50 天
        notes = [
            "short note",
            f"hit_symbols: {hit_symbols}",  # 这条会很长
        ]

        result = _truncate_notes(notes, max_size=1024)

        total_size = sum(len(n.encode("utf-8")) for n in result)
        assert total_size <= 1024
        assert "[notes truncated due to size limit]" in result

    def test_notes_size_calculation_correct(self):
        """notes 大小计算正确（UTF-8）"""
        # 中文字符在 UTF-8 中占 3 字节
        notes = ["中文测试"]  # 4 个字符 * 3 = 12 字节
        result = _truncate_notes(notes, max_size=10)

        # 12 字节 > 10 字节，需要截断
        assert len(result) == 1
        assert "[notes truncated due to size limit]" in result