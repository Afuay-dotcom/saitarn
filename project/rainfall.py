"""
rainfall.py
===========
ฝนสะสม ณ พิกัดผู้ใช้ จาก Open-Meteo (ฟรี ไม่ต้องใช้ API key สำหรับงานที่ไม่ใช่เชิงพาณิชย์)

ข้อควรระวัง (ต้องเขียนในเล่ม/บอกผู้ใช้):
  - เป็นค่าประมาณจากแบบจำลองอากาศบนกริด ไม่ใช่ค่าจากเครื่องวัดฝนจริง
    ฝนตกหนักเฉพาะจุดอาจถูกประเมินต่ำกว่าจริง
  - ฝนสะสมสูง = "ตัวชี้ความเสี่ยงน้ำท่วมขัง" ไม่ใช่การยืนยันว่าท่วมจริง
  - Open-Meteo ฟรีเฉพาะการใช้งานที่ไม่ใช่เชิงพาณิชย์
"""

from datetime import date, datetime, timedelta, timezone

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"   # ข้อมูลล่าสุด (+ย้อนหลังไม่กี่วัน)
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"  # ข้อมูลย้อนหลัง (มีดีเลย์ไม่กี่วัน)
TIMEZONE = "Asia/Bangkok"
REQUEST_TIMEOUT = 10

# วันที่ใหม่กว่านี้ (วัน) ใช้ forecast API ที่ย้อนหลังได้ ส่วนเก่ากว่านี้ใช้ archive
# (ค่า 7 เป็นข้อสันนิษฐานของผู้จัดทำว่า archive มีดีเลย์ไม่เกินนี้ ปรับได้)
ARCHIVE_MIN_AGE_DAYS = 7

_BKK = timezone(timedelta(hours=7))  # ไทยไม่มี DST

# เกณฑ์ระดับฝน 24 ชม. (มม.) ตามการจำแนกของกรมอุตุนิยมวิทยา
# *** ตัวเลขนี้เป็นค่าที่อ้างกันทั่วไป แต่ผู้จัดทำยังยืนยันกับเอกสารต้นทางของกรมอุตุฯ ไม่ได้
#     ก่อนใส่ในเล่ม ให้ตรวจกับเว็บ/เอกสาร tmd.go.th แล้วแก้ที่นี่ที่เดียว ***
RAIN_THRESHOLDS_MM = {"ปานกลาง": 10.0, "หนัก": 35.0, "หนักมาก": 90.0}


def classify_rain_24h(mm):
    """จำแนกระดับฝนจากปริมาณฝน 24 ชม. (มม.)"""
    if mm is None:
        return None
    if mm > RAIN_THRESHOLDS_MM["หนักมาก"]:
        return "ฝนหนักมาก"
    if mm > RAIN_THRESHOLDS_MM["หนัก"]:
        return "ฝนหนัก"
    if mm > RAIN_THRESHOLDS_MM["ปานกลาง"]:
        return "ฝนปานกลาง"
    if mm >= 0.1:
        return "ฝนเล็กน้อย"
    return "ไม่มีฝน"


def is_high_rain(level):
    return level in ("ฝนหนัก", "ฝนหนักมาก")


def _now_bkk_naive():
    return datetime.now(_BKK).replace(tzinfo=None)


def get_recent_rainfall(lat, lng, get=requests.get, now=None):
    """
    ฝนสะสม 24 และ 72 ชั่วโมงล่าสุด ณ พิกัด (นับจากชั่วโมงปัจจุบัน ไม่รวมค่าพยากรณ์ล่วงหน้า)
    คืน dict หรือ None ถ้าไม่มีข้อมูล
    """
    params = {
        "latitude": lat, "longitude": lng,
        "hourly": "precipitation", "past_days": 3, "forecast_days": 1,
        "timezone": TIMEZONE,
    }
    resp = get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    hourly = resp.json().get("hourly") or {}
    times, values = hourly.get("time") or [], hourly.get("precipitation") or []

    now = now or _now_bkk_naive()
    sum24 = sum72 = 0.0
    valid = 0
    for t, v in zip(times, values):
        if v is None:
            continue
        try:
            ts = datetime.fromisoformat(t)
        except ValueError:
            continue
        # ค่าของชั่วโมง t = ฝนสะสมในชั่วโมงก่อนหน้า t -> นับเฉพาะ t <= ตอนนี้
        if ts > now:
            continue
        if ts > now - timedelta(hours=72):
            sum72 += v
            valid += 1
            if ts > now - timedelta(hours=24):
                sum24 += v
    if valid == 0:
        return None
    return {
        "rain_24h_mm": round(sum24, 1),
        "rain_72h_mm": round(sum72, 1),
        "level_24h": classify_rain_24h(sum24),
        "as_of": now.strftime("%Y-%m-%d %H:%M"),
    }


def get_rainfall_on_date(lat, lng, day: date, get=requests.get, today=None):
    """
    ฝนรวมทั้งวันของวันที่ที่ระบุ (ตามเวลาไทย)
    คืน dict: status = "ok" | "future" | "no_data"
    """
    today = today or _now_bkk_naive().date()
    if day > today:
        return {"status": "future", "date": day.isoformat()}

    age_days = (today - day).days
    if age_days <= ARCHIVE_MIN_AGE_DAYS:
        params = {"latitude": lat, "longitude": lng, "daily": "precipitation_sum",
                  "past_days": age_days, "forecast_days": 1, "timezone": TIMEZONE}
        url, source = FORECAST_URL, "forecast"
    else:
        params = {"latitude": lat, "longitude": lng, "daily": "precipitation_sum",
                  "start_date": day.isoformat(), "end_date": day.isoformat(), "timezone": TIMEZONE}
        url, source = ARCHIVE_URL, "archive"

    resp = get(url, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    daily = resp.json().get("daily") or {}
    times, sums = daily.get("time") or [], daily.get("precipitation_sum") or []

    for t, v in zip(times, sums):
        if t == day.isoformat() and v is not None:
            return {"status": "ok", "date": t, "rain_mm": round(v, 1),
                    "level": classify_rain_24h(v), "source": source}
    return {"status": "no_data", "date": day.isoformat()}


# ---------------------------------------------------------------------------
# ข้อความสำหรับ LINE
# ---------------------------------------------------------------------------

RAIN_CAVEAT = "(ค่าประมาณจากแบบจำลองอากาศ ไม่ใช่เครื่องวัดฝนจริง)"
RAIN_RISK_NOTE = ("⚠️ ฝนสะสมสูง อาจเกิดน้ำท่วมขังในพื้นที่ลุ่มหรือที่ระบายน้ำไม่ทัน "
                  "(เป็นตัวบอกความเสี่ยง ไม่ได้ยืนยันว่าท่วมจริง)")


def format_recent_rain_lines(rain):
    if not rain:
        return ["🌧️ ไม่สามารถดึงข้อมูลฝนสะสมได้ในขณะนี้"]
    lines = [f"🌧️ ฝนสะสม 24 ชม.ล่าสุด: {rain['rain_24h_mm']} มม. ({rain['level_24h']}) "
             f"| 72 ชม.: {rain['rain_72h_mm']} มม. {RAIN_CAVEAT}"]
    if is_high_rain(rain["level_24h"]) or rain["rain_72h_mm"] >= 3 * RAIN_THRESHOLDS_MM["หนัก"]:
        lines.append(RAIN_RISK_NOTE)
    return lines
