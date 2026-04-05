"""
chopper.chart — 星盘计算核心模块
使用 ephem 计算行星位置、上升点、顶点
"""

import ephem
import pytz
from datetime import datetime
from typing import Optional
import math

# 城市经纬度缓存
LOCATION_CACHE = {
    "北京": ("39.9042", "116.4074"),
    "上海": ("31.2304", "121.4737"),
    "广州": ("23.1291", "113.2644"),
    "深圳": ("22.5431", "114.0579"),
    "杭州": ("30.2741", "120.1551"),
    "成都": ("30.5728", "104.0665"),
    "香港": ("22.3193", "114.1694"),
    "澳门": ("22.1987", "113.5491"),
    "台北": ("25.0330", "121.5654"),
}


def _parse_location(location: str) -> tuple[str, str]:
    """解析出生地为经纬度"""
    # 如果是 "lat,lon" 格式
    if "," in location:
        parts = location.split(",")
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    # 查缓存
    for city, coords in LOCATION_CACHE.items():
        if city in location or location in city:
            return coords[0], coords[1]
    raise ValueError(
        f"未知地点: {location}。请提供 'lat,lon' 格式的经纬度，"
        f"或使用以下已知城市之一: {', '.join(LOCATION_CACHE.keys())}"
    )


def _normalize_degree(deg: float) -> float:
    """将角度标准化到 0-360"""
    return deg % 360


def _degree_to_sign(deg: float) -> tuple[str, float]:
    """将黄道度数转换为星座与相位"""
    signs = [
        "♈ 白羊座", "♉ 金牛座", "♊ 双子座", "♋ 巨蟹座",
        "♌ 狮子座", "♍ 处女座", "♎ 天秤座", "♏ 天蝎座",
        "♐ 射手座", "♑ 摩羯座", "♒ 水瓶座", "♓ 双鱼座",
    ]
    sign_index = int(deg // 30)
    degree_in_sign = deg % 30
    return signs[sign_index], round(degree_in_sign, 1)


def _estimate_house_cusp(jd: float, lat: float, lst: float) -> list[float]:
    """使用简化 Placidus 体系估算宫头度数（精确版需要完整库）"""
    cusps = []
    for i in range(12):
        # 粗略估计：每宫 30°，按地方恒星时旋转
        cusp_lon = (lst * 15 + i * 30) % 360
        cusps.append(round(cusp_lon, 2))
    return cusps





def _calc_planet_sign(planet_body, date_time) -> tuple[str, float]:
    """计算行星所在星座与度数（RA/Dec → 热带黄道经度）"""
    planet_body.compute(date_time)
    eps = math.radians(23.44)  # 黄道倾斜角
    # 岁差修正：1990年约 +23.44°（每世纪约增 1.4°）
    PRECESSION_OFFSET = 23.44

    # ephem.Body.ra/dec 是 Angle 对象，除以 ephem.degree 得十进制度数
    ra = float(planet_body.ra) / ephem.degree
    dec = float(planet_body.dec) / ephem.degree
    ra_rad = math.radians(ra)
    dec_rad = math.radians(dec)

    # RA/Dec → 恒星黄道经度
    lon = math.atan2(
        math.sin(ra_rad) * math.cos(eps) + math.tan(dec_rad) * math.sin(eps),
        math.cos(ra_rad)
    )
    lon = _normalize_degree(math.degrees(lon))
    # 加上岁差修正 → 热带黄道坐标（西方占星标准）
    lon = (lon + PRECESSION_OFFSET) % 360

    sign, deg = _degree_to_sign(lon)
    return sign, round(lon % 30, 1)


def calculate(
    birth_date: str,
    birth_time: str,
    birth_location: str,
    timezone: Optional[str] = None,
) -> dict:
    """
    计算完整星盘

    参数:
        birth_date: 出生日期，格式 YYYY-MM-DD
        birth_time: 出生时间，格式 HH:MM
        birth_location: 城市名或 "lat,lon"
        timezone: IANA 时区，默认从地点推断

    返回:
        包含 7 颗行星位置 + 相位 + 元数据的字典
    """
    # 1. 解析地点
    lat_str, lon_str = _parse_location(birth_location)
    lat = float(lat_str)
    lon = float(lon_str)

    # 2. 解析时间
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    
    # 3. 处理时区
    if timezone is None:
        # 简单时区推断（生产环境建议用 pytz 或地理库）
        timezone = "Asia/Shanghai"  # 默认东八区
    
    try:
        tz = pytz.timezone(timezone)
    except Exception:
        tz = pytz.timezone("Asia/Shanghai")
    
    local_dt = tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)

    # 4. 构建 ephem 日期
    ephem_date = utc_dt.strftime("%Y/%m/%d %H:%M:%S")

    # 5. 计算地方恒星时 (LST)
    # 使用 ephem 计算
    eq = ephem.Equatorial(0, 0, epoch=0)
    # 简化：直接用 ephem 的 sidereal_time 近似
    # 精确的 LST 需要知道 UT
    ut_hour = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    jd = ephem.Date(ephem_date)
    
    # LST = 100.46 + 0.985647 * (d) + lon/15
    # d = 从 J2000 后的天数
    j2000 = ephem.Date("2000/1/1 12:00:00")
    d = jd - j2000
    lst_deg = 100.46 + 0.985647 * d + lon / 15
    lst_hour = lst_deg / 15  # 转为小时
    lst_hour = lst_hour % 24

    # 6. 计算各行星
    planets = {}
    bodies = {
        "sun": ephem.Sun(),
        "moon": ephem.Moon(),
        "mercury": ephem.Mercury(),
        "venus": ephem.Venus(),
        "mars": ephem.Mars(),
    }

    for name, body in bodies.items():
        sign, deg = _calc_planet_sign(body, ephem_date)
        planets[name] = {"sign": sign, "degree": deg}

    # 7. 计算上升点 (ASC)
    # ASC = arctan(sin(LST*15) / cos(LST*15) * cos(obliquity) - tan(lat)*sin(obliquity))
    lst_rad = math.radians(lst_hour * 15)
    lat_rad = math.radians(lat)
    # 黄道倾斜角 ~23.44°
    obliq = math.radians(23.44)
    
    asc_rad = math.atan2(
        math.sin(lst_rad) * math.cos(obliq),
        math.cos(lst_rad) * math.cos(lat_rad) + math.sin(lat_rad) * math.tan(obliq)
    )
    asc_deg = math.degrees(asc_rad)
    asc_deg = _normalize_degree(asc_deg)
    asc_sign, asc_degree = _degree_to_sign(asc_deg)
    planets["asc"] = {"sign": asc_sign, "degree": asc_degree}

    # 8. 计算顶点 (MC) — 简化
    mc_deg = (lst_deg + 180) % 360
    mc_sign, mc_degree = _degree_to_sign(mc_deg)
    planets["mc"] = {"sign": mc_sign, "degree": mc_degree}

    # 9. 婚神星 Juno — 纯轨道力学计算（无需额外库）
    # J2000.0 轨道根数
    L0 = math.radians(247.86)   # 初始平黄经 (deg)
    omega_peri = math.radians(33.32)  # 近日点幅角
    e = 0.2559                  # 离心率
    n = 0.00834788              # 平均每日运动 (rad/day) — 对应 4.36年周期
    Om = math.radians(170.00)  # 升交点经度

    # 计算目标日期的儒略日
    d0 = ephem.julian_date("2000/1/1 12:00:00")
    d1 = ephem.julian_date(ephem_date)
    days_elapsed = d1 - d0

    # 平黄经
    M = (L0 + n * days_elapsed) % (2 * math.pi)
    # Kepler 方程迭代求偏近点角 E
    E = M
    for _ in range(10):
        E = M + e * math.sin(E)
    # 真近点角 v
    nu = 2 * math.atan2(
        math.sqrt(1 + e) * math.sin(E / 2),
        math.sqrt(1 - e) * math.cos(E / 2)
    )
    # 黄道经度 λ = ω + Ω + ν
    juno_lon = _normalize_degree(
        math.degrees(omega_peri + Om + nu)
    )
    juno_sign, juno_degree = _degree_to_sign(juno_lon)
    planets["juno"] = {"sign": juno_sign, "degree": round(juno_lon % 30, 1)}

    # 10. 计算主要相位
    aspects = _calc_aspects(planets)

    return {
        "sun": planets["sun"],
        "moon": planets["moon"],
        "asc": planets["asc"],
        "venus": planets["venus"],
        "mars": planets["mars"],
        "mercury": planets["mercury"],
        "juno": planets["juno"],
        "aspects": aspects,
        "metadata": {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "location": birth_location,
            "tz": timezone,
            "sidereal_time": round(lst_hour, 4),
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
        }
    }


def _calc_aspects(planets: dict) -> list[dict]:
    """计算主要相位"""
    aspects_out = []
    
    # 主要相位定义
    aspect_defs = [
        ("sun", "moon"),
        ("sun", "venus"),
        ("sun", "mars"),
        ("sun", "mercury"),
        ("moon", "venus"),
        ("moon", "mars"),
        ("moon", "mercury"),
        ("venus", "mars"),
        ("mercury", "venus"),
        ("mercury", "mars"),
    ]
    
    for p1, p2 in aspect_defs:
        try:
            lon1 = planets[p1]["degree"] + _sign_index(planets[p1]["sign"]) * 30
            lon2 = planets[p2]["degree"] + _sign_index(planets[p2]["sign"]) * 30
            angle = abs(lon1 - lon2)
            if angle > 180:
                angle = 360 - angle
            
            aspect_name, aspect_angle, orb_limit = _identify_aspect(angle)
            if aspect_name and orb_limit:
                orb = abs(angle - aspect_angle)
                if orb <= orb_limit:
                    aspects_out.append({
                        "p1": p1,
                        "p2": p2,
                        "angle": round(angle, 1),
                        "aspect": f"{aspect_name}({aspect_angle}°)",
                        "orb": round(orb, 1),
                    })
        except Exception:
            continue
    
    return aspects_out


def _sign_index(sign: str) -> int:
    """获取星座索引"""
    signs = [
        "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓",
    ]
    for i, s in enumerate(signs):
        if s in sign:
            return i
    return 0


def _identify_aspect(angle: float) -> tuple:
    """识别相位类型"""
    targets = [
        ("合相", 0, 8.0),
        ("六分相", 60, 6.0),
        ("四分相", 90, 8.0),
        ("三分相", 120, 8.0),
        ("对分相", 180, 8.0),
    ]
    for name, target, orb in targets:
        if abs(angle - target) <= orb:
            return name, target, orb
    return None, None, None


if __name__ == "__main__":
    # 快速测试
    result = calculate("1990-06-15", "14:30", "上海")
    print(result)
