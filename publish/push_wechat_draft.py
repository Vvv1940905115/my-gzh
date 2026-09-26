#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin CLI entry point; the implementation lives in wechat_push.py."""

import sys
sys.dont_write_bytecode = True
from pathlib import Path

_PUBLISH_DIR = Path(__file__).resolve().parent
if str(_PUBLISH_DIR) not in sys.path:
    sys.path.insert(0, str(_PUBLISH_DIR))

from wechat_push import main  # noqa: E402,F401

if __name__ == "__main__":
    main()
