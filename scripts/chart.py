#!/usr/bin/env python3
"""
Chopper Astrology — Swiss Ephemeris 本地占星计算器

用法：
  python3 scripts/chart.py --json \
    --birth-date=YYYY-MM-DD \
    --birth-time=HH:MM \
    --birth-location="地址" \
    --birth-time-precision=exact|estimated|approximate|unknown \
    --timezone=Asia/Shanghai

  python3 scripts/chart.py --version

真值源：Swiss Ephemeris (pyswisseph / swisseph)
"""

import sys
import json
import math
import argparse
from datetime import datetime

# ---- Swiss Ephemeris import (兼容多种包名) ----
try:
    import swisseph as swe
    SWE_MODULE = "swisseph"
except ImportError:
    try:
        import pyswisseph as swe
        SWE_MODULE = "pyswisseph"
    except ImportError:
        print(json.dumps({
            "error": "dependency_missing",
            "message": "Swiss Ephemeris 未安装。请运行: pip install pyswisseph"
        }, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

# Unicode 星座符号：\u2648(Aries)~\u2653(Pisces)
ZODIAC_SIGNS = [
    ("\u2648", "\u767d\u7f8a\u5ea7"),   # 0 Aries
    ("\u2649", "\u91d1\u725b\u5ea7"),   # 1 Taurus
    ("\u264a", "\u53cc\u5b50\u5ea7"),   # 2 Gemini
    ("\u264b", "\u5de8\u87f9\u5ea7"),   # 3 Cancer
    ("\u264c", "\u72ee\u5b50\u5ea7"),   # 4 Leo
    ("\u264d", "\u5904\u5973\u5ea7"),   # 5 Virgo
    ("\u264e", "\u5929\u79e4\u5ea7"),   # 6 Libra
    ("\u264f", "\u5929\u874c\u5ea7"),   # 7 Scorpio
    ("\u2650", "\u5c04\u624b\u5ea7"),   # 8 Sagittarius
    ("\u2651", "\u6469\u7fdf\u5ea7"),   # 9 Capricorn
    ("\u2652", "\u6c34\u74f6\u5ea7"),   # 10 Aquarius
    ("\u2653", "\u53cc\u9c7c\u5ea7"),   # 11 Pisces
]

# Swiss Ephemeris 行星常数
SWE_PLANETS = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mercury": swe.MERCURY,
    "venus": swe.VENUS,
    "mars": swe.MARS,
}

# 主要相位容许度 (orb in degrees)
ORB_CONJUNCTION = 8.0
ORB_OPPOSITION = 8.0
ORB_TRINE = 8.0
ORB_SQUARE = 8.0
ORB_SEXTILE = 6.0

# 相位类型定义
ASPECT_TYPES = [
    ("conjunction", 0, ORB_CONJUNCTION),
    ("sextile", 60, ORB_SEXTILE),
    ("square", 90, ORB_SQUARE),
    ("trine", 120, ORB_TRINE),
    ("opposition", 180, ORB_OPPOSITION),
]


def normalize_angle(a):
    """Normalize angle to [0, 360)."""
    return a % 360.0


def angle_diff(a, b):
    """Difference between two angles in [0, 180]."""
    d = abs(a - b) % 360.0
    if d > 180.0:
        d = 360.0 - d
    return d


def lon_to_sign(lon):
    """Convert ecliptic longitude to sign symbol, name, and degree in sign."""
    idx = int(lon // 30.0) % 12
    deg_in_sign = round(lon % 30.0, 2)
    symbol, name = ZODIAC_SIGNS[idx]
    return symbol, name, deg_in_sign, idx


def julday_from_datetime(dt):
    """Convert timezone-aware datetime to Julian Day (TT)."""
    # Convert to UTC
    utc_dt = dt.astimezone(_UTC())
    # Convert naive UTC to JD
    jd_utc = swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    )
    # TT = UTC + 32.184 seconds
    return jd_utc + 32.184 / 86400.0


def _UTC():
    """Get pytz UTC or fallback."""
    try:
        import pytz
        return pytz.UTC
    except ImportError:
        # Fallback without pytz: assume UTC
        from datetime import timezone
        return timezone.utc


def calc_planet(jd_tt, planet_id):
    """Calculate planet ecliptic longitude using Swiss Ephemeris."""
    res = swe.calc(jd_tt, planet_id, swe.FLG_SWIEPH)
    lon = res[0][0]          # ecliptic longitude degrees
    lat = res[0][1]          # ecliptic latitude degrees
    dist = res[0][2]         # distance
    speed_lon = res[0][3]    # speed in longitude deg/day
    return {
        "lon": round(lon, 4),
        "lat": round(lat, 4),
        "dist": round(dist, 6),
        "speed_lon": round(speed_lon, 6),
    }


def calc_asc_mc(jd_tt, lat, lon):
    """Calculate Ascendant and Midheaven using Swiss Ephemeris houses()."""
    houses, ascmc = swe.houses(jd_tt, lat, lon, b'P')
    asc = ascmc[0]
    mc = ascmc[1]
    armc = ascmc[2]
    return {
        "asc": round(asc, 4),
        "mc": round(mc, 4),
        "armc": round(armc, 4),
        "house_cusps": [round(h, 4) for h in houses],
    }


def get_planet_sign(planet_lon):
    """Get zodiac sign info for a planet longitude."""
    symbol, name, deg, idx = lon_to_sign(planet_lon)
    return {
        "sign": symbol,
        "sign_name": name,
        "sign_index": idx,
        "degree": deg,
        "lon": planet_lon,
    }


def planet_in_house(planet_lon, asc_lon, house_cusps):
    """Determine which house a planet is in (1-12)."""
    # Normalize all angles
    asc_n = normalize_angle(asc_lon)
    p_n = normalize_angle(planet_lon)
    hc_n = [normalize_angle(h) for h in house_cusps]

    # Calculate angular distance from ASC for planet and house cusps
    def from_asc(angle):
        d = normalize_angle(angle - asc_n)
        return d

    p_from_asc = from_asc(p_n)

    for i, cusp in enumerate(hc_n):
        cusp_from_asc = from_asc(cusp)
        next_cusp_from_asc = from_asc(hc_n[(i + 1) % 12])

        # Check if planet is between this cusp and next
        if next_cusp_from_asc > cusp_from_asc:
            in_range = cusp_from_asc <= p_from_asc < next_cusp_from_asc
        else:
            # Wraps around 360°
            in_range = p_from_asc >= cusp_from_asc or p_from_asc < next_cusp_from_asc

        if in_range:
            return i + 1  # house numbers are 1-12

    return 12  # fallback


def identify_aspect(lon1, lon2):
    """Check if two longitudes form an aspect. Returns (type, orb) or None."""
    diff = angle_diff(lon1, lon2)
    for aspect_name, target_angle, orb in ASPECT_TYPES:
        if abs(diff - target_angle) <= orb:
            return aspect_name, round(abs(diff - target_angle), 2)
    return None


def build_aspects(planet_lons, precision):
    """
    Calculate aspects between planets.
    planet_lons: dict {name: longitude}
    precision: 'exact', 'estimated', 'approximate', 'unknown'
    Returns list of aspect dicts.
    """
    if precision in ("approximate", "unknown", "estimated"):
        return []

    names = list(planet_lons.keys())
    aspects = []
    checked = set()

    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            if (n1, n2) in checked:
                continue
            result = identify_aspect(planet_lons[n1], planet_lons[n2])
            if result:
                aspect_name, orb = result
                # Determine confidence
                if orb <= 2.0:
                    conf = "high"
                elif orb <= 5.0:
                    conf = "medium"
                else:
                    conf = "low"

                # For estimated precision, reduce confidence
                if precision == "estimated":
                    conf = "low" if conf == "high" else conf

                aspects.append({
                    "p1": n1,
                    "p2": n2,
                    "lon1": round(planet_lons[n1], 4),
                    "lon2": round(planet_lons[n2], 4),
                    "angle": round(angle_diff(planet_lons[n1], planet_lons[n2]), 2),
                    "type": aspect_name,
                    "orb": orb,
                    "confidence": conf,
                })
                checked.add((n1, n2))

    return aspects


def build_confidence(precision):
    """Build confidence dict based on precision level."""
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
            "overall": "high",
            "sun": "high", "moon": "high",
            "mercury": "medium", "venus": "medium", "mars": "medium",
            "ascendant": "high", "midheaven": "high",
            "houses": "high",
            "aspects_fast": "medium", "aspects_slow": "medium",
        })
    elif precision == "estimated":
        base.update({
            "overall": "medium",
            "sun": "high", "moon": "medium",
            "mercury": "medium", "venus": "medium", "mars": "medium",
            "ascendant": "medium", "midheaven": "medium",
            "houses": "unavailable",
            "aspects_fast": "unavailable", "aspects_slow": "unavailable",
        })
    elif precision == "approximate":
        base.update({
            "overall": "low",
            "sun": "low", "moon": "unavailable",
            "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
            "ascendant": "low", "midheaven": "low",
            "houses": "unavailable",
            "aspects_fast": "unavailable", "aspects_slow": "unavailable",
        })
    else:  # unknown
        base.update({
            "overall": "unavailable",
            "sun": "low", "moon": "unavailable",
            "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
            "ascendant": "unavailable", "midheaven": "unavailable",
            "houses": "unavailable",
            "aspects_fast": "unavailable", "aspects_slow": "unavailable",
        })

    return base


def build_warnings(precision):
    """Build warning list based on precision."""
    warnings = []
    if precision == "estimated":
        warnings.append({
            "code": "BIRTH_TIME_ESTIMATED",
            "field": "birth_time",
            "message": "出生时间为估算值，相位不可用",
            "affected": ["ascendant", "midheaven", "aspects"],
        })
    elif precision == "approximate":
        warnings.append({
            "code": "BIRTH_TIME_APPROXIMATE",
            "field": "birth_time",
            "message": "出生时间仅有模糊区间，仅太阳星座可用",
            "affected": ["moon", "mercury", "venus", "mars", "ascendant", "midheaven", "houses", "aspects"],
        })
    elif precision == "unknown":
        warnings.append({
            "code": "BIRTH_TIME_UNKNOWN",
            "field": "birth_time",
            "message": "出生时间完全未知，或计算器不可用。太阳星座置信度降为 low，不得声称精确。",
            "affected": ["sun", "moon", "mercury", "venus", "mars", "ascendant", "midheaven", "houses", "aspects"],
        })
    return warnings


def build_data_source(precision):
    """Return data_source string based on precision."""
    if precision == "unknown":
        return "unavailable"
    return "swe_local"


def build_reference_test_output():
    """
    生成对照测试基准输出（使用标准测试用例）。
    出生信息：2002-08-16 11:30 北京时间
    地点：安徽省六安市霍邱县 (lat=32.0, lon=116.0)
    用于与成熟排盘软件（如 Astro.com、Solar Fire）逐项核对。
    """
    lat, lon = 32.0, 116.0
    tz_name = "Asia/Shanghai"
    birth_dt = datetime(2002, 8, 16, 11, 30)

    try:
        import pytz
        tz = pytz.timezone(tz_name)
        local_dt = tz.localize(birth_dt)
        utc_dt = local_dt.astimezone(pytz.utc)
        jd_tt = swe.julday(
            utc_dt.year, utc_dt.month, utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
        ) + 32.184 / 86400.0
    except ImportError:
        # julday(year, month, day, hour_float)
        jd_tt = swe.julday(2002, 8, 16, 3.5) + 32.184 / 86400.0

    # 计算所有行星
    planet_raw = {}
    for name, pid in SWE_PLANETS.items():
        planet_raw[name] = calc_planet(jd_tt, pid)

    # 计算 ASC/MC
    asc_mc = calc_asc_mc(jd_tt, lat, lon)

    # 组装结构
    planets = {}
    for name, raw in planet_raw.items():
        info = get_planet_sign(raw["lon"])
        planets[name] = {
            "sign": info["sign"],
            "sign_name": info["sign_name"],
            "sign_index": info["sign_index"],
            "degree_in_sign": info["degree"],
            "ecliptic_lon": raw["lon"],
            "ecliptic_lat": raw["lat"],
        }

    return {
        "meta": {
            "reference_utc": utc_dt.isoformat() if 'utc_dt' in dir() else "2002-08-16T03:30:00+00:00",
            "jd_tt": round(jd_tt, 6),
            "location": {"lat": lat, "lon": lon, "tz": tz_name},
            "asc_mc": asc_mc,
            "planets_raw": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                              for kk, vv in v.items()} for k, v in planet_raw.items()},
        },
        "chart": {
            "planets": planets,
            "ascendant": {
                "lon": asc_mc["asc"],
                **get_planet_sign(asc_mc["asc"]),
            },
            "midheaven": {
                "lon": asc_mc["mc"],
                **get_planet_sign(asc_mc["mc"]),
            },
        },
    }


def calculate_chart(birth_date, birth_time, precision, lat, lon, tz_name):
    """
    Main chart calculation.
    Returns (planets_dict, asc_mc_dict, aspects_list).
    Precision-based planet filtering:
      exact:     all 5 planets + ASC/MC + houses + aspects
      estimated: all 5 planets + ASC/MC (no houses) + no aspects
      approximate: sun only + ASC/MC (low conf)
      unknown:   sun only (low conf)
    """
    # Parse datetime
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")

    # Get JD in TT
    try:
        import pytz
        tz = pytz.timezone(tz_name)
        local_dt = tz.localize(dt)
        utc_dt = local_dt.astimezone(pytz.utc)
        jd_tt = swe.julday(
            utc_dt.year, utc_dt.month, utc_dt.day,
            utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
        ) + 32.184 / 86400.0
    except ImportError:
        # Fallback: assume input is UTC
        jd_tt = swe.julday(dt.year, dt.month, dt.day,
                           dt.hour + dt.minute / 60.0 + dt.second / 3600.0)

    # Calculate ALL planets (for reference), then filter
    planet_raw = {}
    for name, pid in SWE_PLANETS.items():
        planet_raw[name] = calc_planet(jd_tt, pid)

    # Calculate ASC/MC
    asc_mc = calc_asc_mc(jd_tt, lat, lon)

    # Determine which planets to include based on precision
    if precision in ("approximate", "unknown"):
        included_planets = ["sun"]
    else:
        included_planets = ["sun", "moon", "mercury", "venus", "mars"]

    # Build planet output with sign info
    planets = {}
    planet_lons = {}
    for name in included_planets:
        raw = planet_raw[name]
        info = get_planet_sign(raw["lon"])
        planet_lons[name] = raw["lon"]
        planets[name] = {
            "sign": info["sign"],
            "sign_name": info["sign_name"],
            "sign_index": info["sign_index"],
            "degree": info["degree"],
            "ecliptic_lon": raw["lon"],
            "ecliptic_lat": raw["lat"],
        }
        # Add house only for exact (full house calculation needs precise time)
        if precision == "exact":
            planets[name]["house"] = planet_in_house(
                raw["lon"], asc_mc["asc"], asc_mc["house_cusps"]
            )

    # Build aspects - only for exact
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
    parser.add_argument("--birth-time-precision", dest="precision",
                       default="exact",
                       choices=["exact", "estimated", "approximate", "unknown"])
    parser.add_argument("--latitude", dest="latitude", type=float, default=None)
    parser.add_argument("--longitude", dest="longitude", type=float, default=None)
    parser.add_argument("--timezone", dest="timezone", default="Asia/Shanghai")
    parser.add_argument("--reference-test", dest="reference_test", action="store_true",
                       help="Output reference test data for cross-check")
    args = parser.parse_args()

    if args.version:
        print(f"chopper-astrology chart.py {swe.version} (Swiss Ephemeris)")
        sys.exit(0)

    if args.reference_test:
        result = build_reference_test_output()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.json:
        # Validate required arguments
        missing = []
        if not args.birth_date:
            missing.append("--birth-date")
        if not args.birth_time:
            missing.append("--birth-time")
        if not args.birth_location:
            missing.append("--birth-location")
        if missing:
            print(json.dumps({
                "error": "missing_required_arguments",
                "message": "缺少必填参数: " + ", ".join(missing)
            }, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

        # For unknown precision, no lat/lon needed (but location is still required for intake)
        # Use provided lat/lon or defaults
        lat = args.latitude if args.latitude is not None else 32.0
        lon = args.longitude if args.longitude is not None else 116.0

        try:
            planets, asc_mc, aspects = calculate_chart(
                args.birth_date, args.birth_time,
                args.precision, lat, lon, args.timezone
            )

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

            # ASC/MC: only for exact and estimated
            if args.precision in ("exact", "estimated"):
                asc_sign_info = lon_to_sign(asc_mc["asc"])
                mc_sign_info = lon_to_sign(asc_mc["mc"])
                output["chart"]["ascendant"] = {
                    "lon": asc_mc["asc"],
                    "sign": asc_sign_info[0],
                    "sign_name": asc_sign_info[1],
                    "sign_index": asc_sign_info[3],
                    "degree": asc_sign_info[2],
                    "house": 1,
                }
                output["chart"]["midheaven"] = {
                    "lon": asc_mc["mc"],
                    "sign": mc_sign_info[0],
                    "sign_name": mc_sign_info[1],
                    "sign_index": mc_sign_info[3],
                    "degree": mc_sign_info[2],
                }
                if args.precision == "exact":
                    output["chart"]["house_cusps"] = asc_mc["house_cusps"]
            else:
                output["chart"].pop("ascendant", None)
                output["chart"].pop("midheaven", None)
                output["chart"].pop("house_cusps", None)

            print(json.dumps(output, ensure_ascii=False, indent=2))
            sys.exit(0)

        except ValueError as e:
            print(json.dumps({"error": "invalid_input", "message": str(e)},
                           ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(json.dumps({"error": "calculation_failed", "message": str(e)},
                           ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":
    main()
