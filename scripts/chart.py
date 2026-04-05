#!/usr/bin/env python3
"""
Chopper Astrology — 本地占星计算器 CLI

用法：
  python3 scripts/chart.py --json \
    --birth-date=YYYY-MM-DD \
    --birth-time=HH:MM \
    --birth-location="地址" \
    --birth-time-precision=exact|estimated|approximate|unknown \
    --timezone=Asia/Shanghai

  python3 scripts/chart.py --version

输出：符合 SKILL.md JSON 契约的结构化 JSON
"""

import sys
import json
import math
import argparse
import ephem
import pytz
from datetime import datetime

# Unicode 符号：\u2648~\u2653（♈♉♊♋♌♍♎♏♐♑♒♓）
SIGNS = [
    ("\u2648", "\u767d\u7f8a\u5ea7"),
    ("\u2649", "\u91d1\u725b\u5ea7"),
    ("\u264a", "\u53cc\u5b50\u5ea7"),
    ("\u264b", "\u5de8\u87f9\u5ea7"),
    ("\u264c", "\u72ee\u5b50\u5ea7"),
    ("\u264d", "\u5904\u5973\u5ea7"),
    ("\u264e", "\u5929\u79e4\u5ea7"),
    ("\u264f", "\u5929\u874c\u5ea7"),
    ("\u2650", "\u5c04\u624b\u5ea7"),
    ("\u2651", "\u6469\u7fdf\u5ea7"),
    ("\u2652", "\u6c34\u74f6\u5ea7"),
    ("\u2653", "\u53cc\u9c7c\u5ea7"),
]


def normalize_degree(d):
    return d % 360


def degree_to_sign(degree):
    idx = int(degree // 30) % 12
    deg_in_sign = round(degree % 30, 1)
    emoji, name = SIGNS[idx]
    return emoji, name, deg_in_sign


def planet_ecliptic_lon(body, ephem_date_str):
    body.compute(ephem_date_str)
    eps = math.radians(23.44)
    PRECESS = 23.44
    ra = float(body.ra) / ephem.degree
    dec = float(body.dec) / ephem.degree
    ra_r = math.radians(ra)
    dec_r = math.radians(dec)
    lon = math.atan2(
        math.sin(ra_r) * math.cos(eps) + math.tan(dec_r) * math.sin(eps),
        math.cos(ra_r)
    )
    return normalize_degree(math.degrees(lon) + PRECESS)


def calc_juno_lon(ephem_date_str):
    L0 = math.radians(247.86)
    omega = math.radians(33.32)
    e = 0.2559
    n = 0.00834788
    Om = math.radians(170.00)
    d0 = ephem.julian_date("2000/1/1 12:00:00")
    d1 = ephem.julian_date(ephem_date_str)
    days = d1 - d0
    M = (L0 + n * days) % (2 * math.pi)
    E = M
    for _ in range(10):
        E = M + e * math.sin(E)
    nu = 2 * math.atan2(
        math.sqrt(1 + e) * math.sin(E / 2),
        math.sqrt(1 - e) * math.cos(E / 2)
    )
    return normalize_degree(math.degrees(omega + Om + nu))


def identify_aspect(angle):
    targets = [
        ("conjunction", 0, 8.0),
        ("sextile", 60, 6.0),
        ("square", 90, 8.0),
        ("trine", 120, 8.0),
        ("opposition", 180, 8.0),
    ]
    for t_type, t_angle, orb in targets:
        if abs(angle - t_angle) <= orb:
            return t_type, round(abs(angle - t_angle), 1)
    return None


def build_confidence(precision):
    base = {
        "moon": "unavailable", "mercury": "unavailable",
        "venus": "unavailable", "mars": "unavailable", "juno": "unavailable",
        "houses": "unavailable", "aspects_fast": "unavailable", "aspects_slow": "unavailable",
    }
    if precision == "exact":
        base.update({
            "overall": "high", "sun": "high", "moon": "high",
            "mercury": "medium", "venus": "medium", "mars": "medium",
            "juno": "low", "aspects_fast": "medium", "aspects_slow": "medium",
        })
    elif precision == "estimated":
        base.update({
            "overall": "medium", "sun": "high", "moon": "medium",
            "mercury": "medium", "venus": "medium", "mars": "medium",
            "aspects_fast": "unavailable", "aspects_slow": "unavailable",
        })
    elif precision == "approximate":
        base.update({"overall": "low", "sun": "low"})
    else:
        base.update({"overall": "unavailable", "sun": "low"})
    return base


def build_warnings(precision):
    codes = {
        "exact": [],
        "estimated": [
            {"code": "BIRTH_TIME_ESTIMATED", "field": "birth_time",
             "message": "出生时间为估算值，相位不可用",
             "affected": ["moon", "aspects"]}
        ],
        "approximate": [
            {"code": "BIRTH_TIME_APPROXIMATE", "field": "birth_time",
             "message": "出生时间仅有模糊区间，仅太阳星座可用",
             "affected": ["moon", "mercury", "venus", "mars", "juno", "aspects"]}
        ],
        "unknown": [
            {"code": "BIRTH_TIME_UNKNOWN", "field": "birth_time",
             "message": "出生时间完全未知，或计算器不可用。太阳星座置信度降为 low，不得声称精确。",
             "affected": ["moon", "mercury", "venus", "mars", "juno", "aspects"]}
        ],
    }
    return codes.get(precision, [])


def build_data_source(precision):
    if precision == "unknown":
        return "unavailable"
    return "local_cli"


def calculate_chart(birth_date, birth_time, precision, timezone_str):
    planets = {}
    aspects = []

    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    tz = pytz.timezone(timezone_str)
    local_dt = tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    ephem_date = utc_dt.strftime("%Y/%m/%d %H:%M:%S")

    sun = ephem.Sun()
    lon = planet_ecliptic_lon(sun, ephem_date)
    emoji, sign_name, deg_in_sign = degree_to_sign(lon)
    planets["sun"] = {
        "sign": emoji, "sign_name": sign_name,
        "degree": deg_in_sign, "raw_lon": round(lon, 1),
    }

    if precision in ("approximate", "unknown"):
        return planets, aspects

    fast_planets = ["moon", "mercury", "venus", "mars"]
    body_classes = {
        "moon": ephem.Moon, "mercury": ephem.Mercury,
        "venus": ephem.Venus, "mars": ephem.Mars,
    }
    for name in fast_planets:
        body = body_classes[name]()
        lon = planet_ecliptic_lon(body, ephem_date)
        emoji, sign_name, deg_in_sign = degree_to_sign(lon)
        planets[name] = {
            "sign": emoji, "sign_name": sign_name,
            "degree": deg_in_sign, "raw_lon": round(lon, 1),
        }

    if precision == "exact":
        juno_lon = calc_juno_lon(ephem_date)
        emoji, sign_name, deg_in_sign = degree_to_sign(juno_lon)
        planets["juno"] = {
            "sign": emoji, "sign_name": sign_name,
            "degree": deg_in_sign, "raw_lon": round(juno_lon, 1),
        }

    if precision == "exact":
        raw_lons = {n: planets[n]["raw_lon"] for n in ["sun", "moon", "mercury", "venus", "mars"]}
        pairs = [
            ("sun", "moon"), ("sun", "mercury"), ("moon", "mercury"),
            ("sun", "venus"), ("moon", "venus"), ("sun", "mars"),
            ("moon", "mars"), ("mercury", "venus"), ("mercury", "mars"),
            ("venus", "mars"),
        ]
        for p1, p2 in pairs:
            diff = abs(raw_lons[p1] - raw_lons[p2])
            if diff > 180:
                diff = 360 - diff
            result = identify_aspect(diff)
            if result:
                t_type, orb = result
                aspects.append({
                    "p1": p1, "p2": p2,
                    "angle": round(diff, 1),
                    "type": t_type,
                    "orb": orb,
                    "confidence": "medium",
                })

    return planets, aspects


def main():
    parser = argparse.ArgumentParser(description="Chopper Astrology — Local Chart Calculator")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--birth-date", dest="birth_date")
    parser.add_argument("--birth-time", dest="birth_time")
    parser.add_argument("--birth-location", dest="birth_location")
    parser.add_argument("--birth-time-precision", dest="precision",
                       default="exact",
                       choices=["exact", "estimated", "approximate", "unknown"])
    parser.add_argument("--timezone", dest="timezone", default="Asia/Shanghai")
    args = parser.parse_args()

    if args.version:
        print("chopper-astrology chart.py 0.1.0")
        sys.exit(0)

    if args.json:
        missing = []
        if not args.birth_date:
            missing.append("--birth-date")
        if not args.birth_time:
            missing.append("--birth-time")
        if not args.birth_location:
            missing.append("--birth-location")
        if missing:
            err = json.dumps({
                "error": "missing_required_arguments",
                "message": "缺少必填参数: " + ", ".join(missing)
            }, ensure_ascii=False)
            print(err, file=sys.stderr)
            sys.exit(1)

        try:
            planets, aspects = calculate_chart(
                args.birth_date, args.birth_time,
                args.precision, args.timezone
            )
            output = {
                "meta": {
                    "data_source": build_data_source(args.precision),
                    "calculator_version": "0.1.0",
                    "generated_at": datetime.now().astimezone(pytz.utc).isoformat(),
                    "confidence": build_confidence(args.precision),
                    "warnings": build_warnings(args.precision),
                    "birth_time_precision": args.precision,
                },
                "input": {
                    "birth_date": args.birth_date,
                    "birth_time": args.birth_time,
                    "birth_time_precision": args.precision,
                    "birth_location": args.birth_location,
                    "latitude": None,
                    "longitude": None,
                    "timezone": args.timezone,
                },
                "chart": {
                    "planets": planets,
                    "aspects": aspects,
                    "patterns": {"identified": [], "notes": "非完整格局分析"},
                },
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            sys.exit(0)
        except ValueError as e:
            err = json.dumps({"error": "invalid_input", "message": str(e)}, ensure_ascii=False)
            print(err, file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            err = json.dumps({"error": "calculation_failed", "message": str(e)}, ensure_ascii=False)
            print(err, file=sys.stderr)
            sys.exit(1)

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
