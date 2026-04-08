"""
对齐分析可视化 — P3-019。

生成可视化报告：
  - 评分雷达图
  - 冲突分布图
  - 评分趋势图
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from src.alignment.types import (
    AlignmentReport,
    ConflictDetection,
    ConflictType,
)
from src.alignment.scoring import DetailedConfidenceScore


# ---------------------------------------------------------------------------
# P3-019: 可视化报告生成
# ---------------------------------------------------------------------------

@dataclass
class ChartData:
    """图表数据。"""
    chart_type: str  # radar, bar, pie, line, heatmap
    title: str
    data: dict[str, Any]
    options: dict[str, Any] | None = None


def generate_radar_chart_data(
    detailed_score: DetailedConfidenceScore,
) -> ChartData:
    """生成评分雷达图数据（P3-019）。

    Args:
        detailed_score: 详细可信度评分

    Returns:
        雷达图数据
    """
    # 提取维度名称和分数
    labels = [dim.name for dim in detailed_score.dimensions]
    scores = [dim.score for dim in detailed_score.dimensions]
    weights = [dim.weight for dim in detailed_score.dimensions]

    data = {
        "labels": labels,
        "datasets": [
            {
                "label": "评分",
                "data": scores,
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 2,
            },
            {
                "label": "权重",
                "data": weights,
                "backgroundColor": "rgba(255, 99, 132, 0.2)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 2,
            },
        ],
    }

    options = {
        "responsive": True,
        "plugins": {
            "legend": {
                "position": "top",
            },
            "title": {
                "display": True,
                "text": f"可信度评分雷达图 - {detailed_score.grade}",
            },
        },
        "scale": {
            "min": 0,
            "max": 1,
        },
    }

    return ChartData(
        chart_type="radar",
        title=f"可信度评分 - {detailed_score.trader_id}",
        data=data,
        options=options,
    )


def generate_conflict_distribution_chart(
    conflicts: ConflictDetection,
) -> ChartData:
    """生成冲突分布图表（P3-019）。

    Args:
        conflicts: 冲突检测结果

    Returns:
        冲突分布数据
    """
    # 按类型统计
    by_type_data = conflicts.by_type.copy()

    # 按严重程度统计
    by_severity_data = conflicts.by_severity.copy()

    data = {
        "by_type": {
            "labels": [ct.split("_")[-1] for ct in by_type_data.keys()],
            "values": list(by_type_data.values()),
            "colors": _get_conflict_type_colors(by_type_data.keys()),
        },
        "by_severity": {
            "labels": list(by_severity_data.keys()),
            "values": list(by_severity_data.values()),
            "colors": _get_severity_colors(by_severity_data.keys()),
        },
    }

    return ChartData(
        chart_type="multi",
        title="冲突分布分析",
        data=data,
    )


def _get_conflict_type_colors(types: dict_keys) -> list[str]:
    """获取冲突类型的颜色映射。"""
    color_map = {
        "rule_contradiction": "rgba(255, 99, 132, 0.7)",
        "rule_overlap": "rgba(255, 159, 64, 0.7)",
        "behavior_deviation": "rgba(255, 205, 86, 0.7)",
        "parameter_mismatch": "rgba(75, 192, 192, 0.7)",
        "temporal_conflict": "rgba(153, 102, 255, 0.7)",
    }
    return [color_map.get(str(t), "rgba(128, 128, 128, 0.7)") for t in types]


def _get_severity_colors(severities: dict_keys) -> list[str]:
    """获取严重程度的颜色映射。"""
    color_map = {
        "critical": "rgba(255, 99, 132, 0.8)",
        "major": "rgba(255, 159, 64, 0.8)",
        "minor": "rgba(75, 192, 192, 0.8)",
    }
    return [color_map.get(str(s), "rgba(128, 128, 128, 0.8)") for s in severities]


def generate_score_bar_chart(
    detailed_score: DetailedConfidenceScore,
) -> ChartData:
    """生成评分柱状图数据（P3-019）。

    Args:
        detailed_score: 详细可信度评分

    Returns:
        柱状图数据
    """
    labels = [dim.name for dim in detailed_score.dimensions]
    scores = [dim.score * 100 for dim in detailed_score.dimensions]
    weights = [dim.weight * 100 for dim in detailed_score.dimensions]

    data = {
        "labels": labels,
        "datasets": [
            {
                "label": "评分 (%)",
                "data": scores,
                "backgroundColor": "rgba(54, 162, 235, 0.7)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1,
            },
            {
                "label": "权重 (%)",
                "data": weights,
                "backgroundColor": "rgba(255, 99, 132, 0.7)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 1,
            },
        ],
    }

    options = {
        "responsive": True,
        "plugins": {
            "legend": {
                "position": "top",
            },
            "title": {
                "display": True,
                "text": f"评分与权重对比 - 综合评分: {detailed_score.overall_score:.1%}",
            },
        },
        "scales": {
            "y": {
                "beginAtZero": True,
                "max": 100,
            },
        },
    }

    return ChartData(
        chart_type="bar",
        title="各维度评分与权重",
        data=data,
        options=options,
    )


def generate_conflict_heatmap(
    conflicts: ConflictDetection,
) -> ChartData:
    """生成冲突热力图数据（P3-019）。

    Args:
        conflicts: 冲突检测结果

    Returns:
        热力图数据
    """
    # 构建冲突矩阵：规则 vs 规则
    all_rules: set[str] = set()
    for conflict in conflicts.conflicts:
        all_rules.update(conflict.involved_rules)

    all_rules = sorted(all_rules)
    n_rules = len(all_rules)

    if n_rules == 0:
        return ChartData(
            chart_type="heatmap",
            title="冲突热力图",
            data={"rules": [], "matrix": []},
        )

    # 初始化冲突矩阵
    matrix = np.zeros((n_rules, n_rules), dtype=float)

    # 填充冲突矩阵
    severity_weights = {"critical": 1.0, "major": 0.6, "minor": 0.3}
    for conflict in conflicts.conflicts:
        involved = conflict.involved_rules
        weight = severity_weights.get(conflict.severity, 0.3)

        for i, r1 in enumerate(all_rules):
            for j, r2 in enumerate(all_rules):
                if r1 in involved and r2 in involved:
                    matrix[i, j] += weight

    # 归一化
    max_val = matrix.max() if matrix.max() > 0 else 1
    matrix = matrix / max_val

    data = {
        "rules": all_rules,
        "matrix": matrix.tolist(),
        "x_label": "规则",
        "y_label": "规则",
    }

    return ChartData(
        chart_type="heatmap",
        title="规则冲突热力图",
        data=data,
    )


def export_chart_data_as_json(
    charts: list[ChartData],
    output_path: Path | str,
) -> None:
    """导出图表数据为 JSON 文件。

    Args:
        charts: 图表数据列表
        output_path: 输出路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chart_dicts = [
        {
            "chart_type": c.chart_type,
            "title": c.title,
            "data": c.data,
            "options": c.options,
        }
        for c in charts
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "charts": chart_dicts,
        }, f, indent=2, ensure_ascii=False)


def generate_html_dashboard(
    trader_id: str,
    detailed_score: DetailedConfidenceScore | None = None,
    conflicts: ConflictDetection | None = None,
    output_path: Path | str | None = None,
) -> str:
    """生成 HTML 可视化仪表板（P3-019）。

    Args:
        trader_id: 交易员 ID
        detailed_score: 详细可信度评分
        conflicts: 冲突检测结果
        output_path: 可选，输出文件路径

    Returns:
        HTML 内容
    """
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>对齐分析仪表板</title>",
        "<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'></script>",
        "<style>",
        _get_dashboard_css(),
        "</style>",
        "</head>",
        "<body>",
        "<div class='container'>",
        f"<h1>对齐分析仪表板 - {trader_id}</h1>",
        f"<p class='timestamp'>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
    ]

    # 添加评分雷达图
    if detailed_score:
        radar_chart = generate_radar_chart_data(detailed_score)
        html_parts.extend([
            "<div class='chart-section'>",
            "<h2>可信度评分</h2>",
            "<canvas id='radarChart'></canvas>",
            "</div>",
        ])

    # 添加冲突分布图
    if conflicts and conflicts.total_conflicts > 0:
        conflict_chart = generate_conflict_distribution_chart(conflicts)
        html_parts.extend([
            "<div class='chart-section'>",
            "<h2>冲突分布</h2>",
            "<canvas id='conflictChart'></canvas>",
            "</div>",
        ])

    # 添加图表数据脚本
    html_parts.append("<script>")
    if detailed_score:
        radar_chart = generate_radar_chart_data(detailed_score)
        html_parts.append(f"const radarData = {json.dumps(radar_chart.data, indent=2)};")
        html_parts.append(f"const radarOptions = {json.dumps(radar_chart.options, indent=2)};")

    if conflicts and conflicts.total_conflicts > 0:
        conflict_chart = generate_conflict_distribution_chart(conflicts)
        html_parts.append(f"const conflictData = {json.dumps(conflict_chart.data, indent=2)};")

    html_parts.append("</script>")
    html_parts.extend([
        "</div>",
        "</body>",
        "</html>",
    ])

    html_content = "\n".join(html_parts)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

    return html_content


def _get_dashboard_css() -> str:
    """获取仪表板 CSS 样式。"""
    return """
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        background-color: #f5f5f5;
        color: #333;
        line-height: 1.6;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    h1 {
        color: #2c3e50;
        margin-bottom: 10px;
    }
    .timestamp {
        color: #7f8c8d;
        font-size: 14px;
        margin-bottom: 30px;
    }
    .chart-section {
        background: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .chart-section h2 {
        color: #34495e;
        margin-bottom: 15px;
        font-size: 18px;
    }
    canvas {
        max-width: 100%;
    }
    .metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 30px;
    }
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card h3 {
        color: #7f8c8d;
        font-size: 14px;
        font-weight: normal;
    }
    .metric-card .value {
        font-size: 32px;
        font-weight: bold;
        color: #2c3e50;
    }
    """


def generate_summary_statistics(
    detailed_score: DetailedConfidenceScore | None,
    conflicts: ConflictDetection | None,
) -> dict[str, Any]:
    """生成汇总统计数据。

    Args:
        detailed_score: 详细可信度评分
        conflicts: 冲突检测结果

    Returns:
        统计数据字典
    """
    stats: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
    }

    if detailed_score:
        stats["overall_score"] = {
            "value": detailed_score.overall_score,
            "grade": detailed_score.grade,
            "grade_label": detailed_score.grade_label,
        }

        stats["dimensions"] = {
            dim.name: {
                "score": dim.score,
                "weight": dim.weight,
                "weighted_score": dim.score * dim.weight,
            }
            for dim in detailed_score.dimensions
        }

    if conflicts:
        stats["conflicts"] = {
            "total": conflicts.total_conflicts,
            "by_type": conflicts.by_type,
            "by_severity": conflicts.by_severity,
        }

    return stats
