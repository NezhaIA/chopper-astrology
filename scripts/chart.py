#!/usr/bin/env python3
"""
Chopper Astrology — Swiss Ephemeris 本地占星计算器

用法：
  python3 scripts/chart.py --json
    --birth-date=YYYY-MM-DD --birth-time=HH:MM
    --birth-location="地址"
    --birth-time-precision=exact|estimated|approximate|unknown
    --latitude=XX.XXXX --longitude=XX.XXXX
    --timezone=Asia/Shanghai

  python3 scripts/chart.py --version
  python3 scripts/chart.py --reference-test

真值源：Swiss Ephemeris (pyswisseph / swisseph)
"""

import sys
import json
import math
import argparse
from datetime import datetime

try:
    import swisseph as swe
except ImportError:
    try:
        import pyswisseph as swe
    except ImportError:
        print(json.dumps({
            "error": "dependency_missing",
            "message": "Swiss Ephemeris 未安装。请运行: pip install pyswisseph"
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

# Unicode 星座符号：\u2648(Aries)~\u2653(Pisces)
ZODIAC_SIGNS = [
    ("\u2648", "\u767d\u7f8a\u5ea7"),
    ("\u2649", "\u91d1\u725b\u5ea7"),
    ("\u264a", "\u53cc\u5b50\u5ea7"),
    ("\u264b", "\u5de8\u87f9\u5ea7"),
    ("\u264c", "\u72ee\u5b50\u5ea7"),
    ("\u264d", "\u5904\u5973\u5ea7"),
    ("\u264e", "\u5929\u79e4\u5ea7"),
    ("\u264f", "\u5929\u874e\u5ea7"),
    ("\u2650", "\u5c04\u624b\u5ea7"),
    ("\u2651", "\u6469\u7faf\u5ea7"),
    ("\u2652", "\u6c34\u74f6\u5ea7"),
    ("\u2653", "\u53cc\u9c7c\u5ea7"),
]

# 标准五行星
SWE_PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
}



# 主要相位容许度
ASPECT_ORBS = [
    ("conjunction", 0, 8.0),
    ("sextile", 60, 6.0),
    ("square", 90, 8.0),
    ("trine", 120, 8.0),
    ("opposition", 180, 8.0),
]


def normalize_angle(a):
    return a % 360.0


def angle_diff(a, b):
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def lon_to_sign(lon):
    idx = int(lon // 30.0) % 12
    deg = round(lon % 30.0, 2)
    symbol, name = ZODIAC_SIGNS[idx]
    return symbol, name, deg, idx


def get_jd_tt(dt, tz_name):
    try:
        import pytz
        tz = pytz.timezone(tz_name)
        utc_dt = tz.localize(dt).astimezone(pytz.utc)
        return swe.julday(
            utc_dt.year, utc_dt.month, utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
        ) + 32.184 / 86400.0
    except ImportError:
        return swe.julday(
            dt.year, dt.month, dt.day,
            dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        )


def calc_planet(jd_tt, planet_id):
    res = swe.calc(jd_tt, planet_id, swe.FLG_SWIEPH)
    return {
        "lon": round(res[0][0], 4),
        "lat": round(res[0][1], 4),
        "dist": round(res[0][2], 6),
        "speed_lon": round(res[0][3], 6),
    }


def calc_asc_mc(jd_tt, lat, lon):
    houses, ascmc = swe.houses(jd_tt, lat, lon, b'P')
    return {
        "asc": round(ascmc[0], 4),
        "mc": round(ascmc[1], 4),
        "armc": round(ascmc[2], 4),
        "house_cusps": [round(h, 4) for h in houses],
    }


def planet_in_house(planet_lon, asc_lon, house_cusps):
    asc_n = normalize_angle(asc_lon)
    p_n = normalize_angle(planet_lon)
    hc_n = [normalize_angle(h) for h in house_cusps]
    p_from_asc = normalize_angle(p_n - asc_n)
    for i in range(12):
        cusp_from = normalize_angle(hc_n[i] - asc_n)
        next_from = normalize_angle(hc_n[(i + 1) % 12] - asc_n)
        in_range = (cusp_from <= p_from_asc < next_from) if next_from > cusp_from \
            else (p_from_asc >= cusp_from or p_from_asc < next_from)
        if in_range:
            return i + 1
    return 12


def identify_aspect(lon1, lon2):
    diff = angle_diff(lon1, lon2)
    for name, angle, orb in ASPECT_ORBS:
        if abs(diff - angle) <= orb:
            return name, round(abs(diff - angle), 2)
    return None


def build_aspects(planet_lons, precision):
    if precision in ("approximate", "unknown", "estimated"):
        return []
    names = list(planet_lons.keys())
    aspects, checked = [], set()
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            if (n1, n2) in checked:
                continue
            result = identify_aspect(planet_lons[n1], planet_lons[n2])
            if result:
                aspect_name, orb = result
                conf = "high" if orb <= 2.0 else ("medium" if orb <= 5.0 else "low")
                aspects.append({
                    "p1": n1, "p2": n2,
                    "lon1": round(planet_lons[n1], 4),
                    "lon2": round(planet_lons[n2], 4),
                    "angle": round(angle_diff(planet_lons[n1], planet_lons[n2]), 2),
                    "type": aspect_name, "orb": orb, "confidence": conf,
                })
                checked.add((n1, n2))
    return aspects


def build_confidence(precision):
    base = {
        "overall": "unavailable",
        "sun": "unavailable", "moon": "unavailable",
        "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
        "ascendant": "unavailable", "midheaven": "unavailable",
        "houses": "unavailable",
        "aspects_fast": "unavailable", "aspects_slow": "unavailable",
    }
    if precision == "exact":
        base.update({
            "overall": "high", "sun": "high", "moon": "high",
            "mercury": "medium", "venus": "medium", "mars": "medium",
            "ascendant": "high", "midheaven": "high",
            "houses": "high",
            "aspects_fast": "medium", "aspects_slow": "medium",
        })
    elif precision == "estimated":
        base.update({
            "overall": "medium", "sun": "high", "moon": "medium",
            "mercury": "medium", "venus": "medium", "mars": "medium",
            "ascendant": "medium", "midheaven": "medium",
            "aspects_fast": "unavailable", "aspects_slow": "unavailable",
        })
    elif precision == "approximate":
        base.update({
            "overall": "low", "sun": "low", "moon": "unavailable",
            "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
        })
    else:
        base.update({
            "overall": "unavailable", "sun": "low",
            "ascendant": "unavailable", "midheaven": "unavailable",
        })
    return base


def build_warnings(precision):
    if precision == "estimated":
        return [{"code": "BIRTH_TIME_ESTIMATED", "field": "birth_time",
                 "message": "出生时间为估算值，相位不可用",
                 "affected": ["ascendant", "midheaven", "aspects"]}]
    if precision == "approximate":
        return [{"code": "BIRTH_TIME_APPROXIMATE", "field": "birth_time",
                 "message": "出生时间仅有模糊区间，仅太阳星座可用",
                 "affected": ["moon", "mercury", "venus", "mars", "ascendant", "midheaven", "houses", "aspects"]}]
    if precision == "unknown":
        return [{"code": "BIRTH_TIME_UNKNOWN", "field": "birth_time",
                 "message": "出生时间完全未知，或计算器不可用。太阳星座置信度降为 low，不得声称精确。",
                 "affected": ["moon", "mercury", "venus", "mars", "ascendant", "midheaven", "houses", "aspects"]}]
    return []


def build_data_source(precision):
    return "swe_local" if precision != "unknown" else "unavailable"


def calculate_chart(birth_date, birth_time, precision, lat, lon, tz_name):
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    jd_tt = get_jd_tt(dt, tz_name)

    planet_raw = {name: calc_planet(jd_tt, pid) for name, pid in SWE_PLANETS.items()}

    has_geo = lat is not None and lon is not None
    asc_mc = calc_asc_mc(jd_tt, lat, lon) if has_geo else None

    # 精度过滤
    if precision in ("approximate", "unknown"):
        included_planets = ["sun"]
    else:
        included_planets = ["sun", "moon", "mercury", "venus", "mars"]

    planets, planet_lons = {}, {}
    for name in included_planets:
        raw = planet_raw[name]
        sym, name_str, deg, idx = lon_to_sign(raw["lon"])
        planet_lons[name] = raw["lon"]
        planets[name] = {
            "sign": sym, "sign_name": name_str, "sign_index": idx,
            "degree": deg, "ecliptic_lon": raw["lon"], "ecliptic_lat": raw["lat"],
        }
        if has_geo and precision == "exact":
            planets[name]["house"] = planet_in_house(
                raw["lon"], asc_mc["asc"], asc_mc["house_cusps"]
            )

    aspects = build_aspects(planet_lons, precision)
    return planets, asc_mc, aspects


def main():
    parser = argparse.ArgumentParser(
        description="Chopper Astrology — Swiss Ephemeris Chart Calculator"
    )
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--birth-date", dest="birth_date")
    parser.add_argument("--birth-time", dest="birth_time")
    parser.add_argument("--birth-location", dest="birth_location")
    parser.add_argument(
        "--birth-time-precision", dest="precision",
        default="exact",
        choices=["exact", "estimated", "approximate", "unknown"]
    )
    parser.add_argument("--latitude", dest="latitude", type=float, default=None)
    parser.add_argument("--longitude", dest="longitude", type=float, default=None)
    parser.add_argument("--timezone", dest="timezone", default="Asia/Shanghai")
    parser.add_argument(
        "--reference-test", dest="reference_test", action="store_true",
        help="对照测试模式：输出完整基准数据，与成熟排盘软件逐项核对"
    )
    args = parser.parse_args()

    if args.version:
        print(f"chopper-astrology chart.py {swe.version} (Swiss Ephemeris)")
        return

    if args.reference_test:
        # 对照测试：固定霍邱坐标，与正常运行路径完全隔离
        lat, lon, tz_name = 32.0, 116.0, "Asia/Shanghai"
        birth_dt = datetime(2002, 8, 16, 11, 30)
        jd_tt = get_jd_tt(birth_dt, tz_name)

        planet_raw = {name: calc_planet(jd_tt, pid) for name, pid in SWE_PLANETS.items()}
        asc_mc = calc_asc_mc(jd_tt, lat, lon)

        planets = {}
        for name, raw in planet_raw.items():
            sym, name_str, deg, idx = lon_to_sign(raw["lon"])
            planets[name] = {
                "sign": sym, "sign_name": name_str, "sign_index": idx,
                "degree": deg, "ecliptic_lon": raw["lon"], "ecliptic_lat": raw["lat"],
                "house": planet_in_house(raw["lon"], asc_mc["asc"], asc_mc["house_cusps"]),
            }

        five_lons = {n: planet_raw[n]["lon"] for n in planet_raw}
        all_aspects = build_aspects(five_lons, "exact")

        result = {
            "mode": "reference_test",
            "description": "五行星对照测试 — 出生信息：2002-08-16 11:30 北京时间，安徽省六安市霍邱县（32°N, 116°E）",
            "birth": {
                "date": "2002-08-16", "time": "11:30",
                "location": "安徽省六安市霍邱县",
                "latitude": lat, "longitude": lon, "timezone": tz_name,
                "local_to_utc_offset_hours": 8,
            },
            "meta": {
                "jd_tt": round(jd_tt, 6),
                "calculator_engine": f"Swiss Ephemeris {swe.version}",
            },
            "ascendant": {
                "lon": asc_mc["asc"],
                "sign": lon_to_sign(asc_mc["asc"])[0],
                "sign_name": lon_to_sign(asc_mc["asc"])[1],
                "degree": lon_to_sign(asc_mc["asc"])[2],
                "house": 1,
            },
            "midheaven": {
                "lon": asc_mc["mc"],
                "sign": lon_to_sign(asc_mc["mc"])[0],
                "sign_name": lon_to_sign(asc_mc["mc"])[1],
                "degree": lon_to_sign(asc_mc["mc"])[2],
            },
            "house_cusps": asc_mc["house_cusps"],
            "planets": planets,
            "aspects": all_aspects,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.json:
        missing = [
            n for n, v in [
                ("--birth-date", args.birth_date),
                ("--birth-time", args.birth_time),
                ("--birth-location", args.birth_location),
            ] if not v
        ]
        if missing:
            print(json.dumps({
                "error": "missing_required_arguments",
                "message": "缺少必填参数: " + ", ".join(missing)
            }, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

        lat, lon = args.latitude, args.longitude
        try:
            planets, asc_mc, aspects = calculate_chart(
                args.birth_date, args.birth_time,
                args.precision, lat, lon, args.timezone
            )
        except Exception as e:
            print(json.dumps({
                "error": "calculation_failed", "message": str(e)
            }, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

        output = {
            "meta": {
                "data_source": build_data_source(args.precision),
                "calculator_engine": f"Swiss Ephemeris {swe.version}",
                "calculator_version": "0.2.0",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "confidence": build_confidence(args.precision),
                "warnings": build_warnings(args.precision),
                "birth_time_precision": args.precision,
            },
            "input": {
                "birth_date": args.birth_date,
                "birth_time": args.birth_time,
                "birth_time_precision": args.precision,
                "birth_location": args.birth_location,
                "latitude": lat,
                "longitude": lon,
                "timezone": args.timezone,
            },
            "chart": {
                "planets": planets,
                "aspects": aspects,
                "patterns": {"identified": [], "notes": "非完整格局分析"},
            },
        }

        if (lat is not None and lon is not None
                and asc_mc is not None and args.precision in ("exact", "estimated")):
            asc_s = lon_to_sign(asc_mc["asc"])
            mc_s = lon_to_sign(asc_mc["mc"])
            output["chart"]["ascendant"] = {
                "lon": asc_mc["asc"],
                "sign": asc_s[0], "sign_name": asc_s[1],
                "sign_index": asc_s[3], "degree": asc_s[2],
                "house": 1,
            }
            output["chart"]["midheaven"] = {
                "lon": asc_mc["mc"],
                "sign": mc_s[0], "sign_name": mc_s[1],
                "sign_index": mc_s[3], "degree": mc_s[2],
            }
            if args.precision == "exact":
                output["chart"]["house_cusps"] = asc_mc["house_cusps"]

        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
