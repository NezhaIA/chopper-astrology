#!/usr/bin/env python3
"""
Chopper Astrology — 首次使用依赖检查脚本

stdout 第一行必须是以下三种状态之一：
  OK:local_cli
  DEGRADED:missing_dependencies
  UNAVAILABLE:calculator_not_found

返回码：0=OK, 1=DEGRADED, 2=UNAVAILABLE
"""

import sys
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_PATH = os.path.join(SCRIPT_DIR, "chart.py")


def check_python_version():
    return sys.version_info >= (3, 9)


def check_dependencies():
    missing = []
    for pkg in ["ephem", "pytz"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def main():
    if not os.path.isfile(CHART_PATH):
        print("UNAVAILABLE:calculator_not_found")
        sys.exit(2)

    if not check_python_version():
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    missing = check_dependencies()
    if missing:
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    try:
        result = subprocess.run(
            [sys.executable, CHART_PATH, "--version"],
            capture_output=True, timeout=5, cwd=SCRIPT_DIR
        )
        if result.returncode != 0:
            print("DEGRADED:missing_dependencies")
            sys.exit(1)
    except Exception:
        print("DEGRADED:missing_dependencies")
        sys.exit(1)

    print("OK:local_cli")
    sys.exit(0)


if __name__ == "__main__":
    main()
