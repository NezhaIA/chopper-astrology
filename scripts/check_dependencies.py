#!/usr/bin/env python3
"""
Chopper Astrology — 首次使用依赖检查脚本

stdout 第一行必须是以下三种状态之一：
  OK:swe_local
  DEGRADED:missing_dependencies
  UNAVAILABLE:calculator_not_found

返回码：0=OK, 1=DEGRADED, 2=UNAVAILABLE
"""

import sys
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH = os.path.join(SCRIPT_DIR, "chart.py")


def check_swe():
    for module_name in ["swisseph", "pyswisseph"]:
        try:
            __import__(module_name)
            return True
        except ImportError:
            continue
    return False


def main():
    if not os.path.isfile(CHART_PATH):
        print("UNAVAILABLE:calculator_not_found")
        sys.exit(2)

    if sys.version_info < (3, 9):
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    try:
        __import__("pytz")
    except ImportError:
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    if not check_swe():
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    try:
        result = subprocess.run(
            [sys.executable, CHART_PATH, "--version"],
            capture_output=True, timeout=10, cwd=SCRIPT_DIR
        )
        if result.returncode != 0:
            print("DEGRADED:missing_dependencies")
            sys.exit(1)
    except Exception:
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    print("OK:swe_local")
    sys.exit(0)


if __name__ == "__main__":
    main()
