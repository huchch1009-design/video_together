#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuarkPan CLI 入口点
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from quark_client.cli.main import app

if __name__ == "__main__":
    app()
