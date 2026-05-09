"""测试全局配置。"""

from __future__ import annotations

import sys
from pathlib import Path


# 让 pytest 在 importlib 模式下也能稳定导入仓库根包。
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
