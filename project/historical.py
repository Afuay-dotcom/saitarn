"""
historical.py
=============
ตอบคำถามแนว "วันที่ X ที่จังหวัด Y ท่วมไหม / ท่วมสูงเท่าไร"

หลักการ: ตอบเฉพาะสิ่งที่ระบบมีข้อมูลจริง และบอกตรงๆ ว่าอะไรที่ระบบ "ไม่มี"
  มี:    ฝนสะสมรายวัน ณ พื้นที่นั้น (Open-Meteo ย้อนหลังได้ทุกวัน, เป็นค่าจากแบบจำลอง)
         ระดับน้ำที่สถานีใกล้สุด (เฉพาะวันที่ระบบเก็บ snapshot ไว้ใน SQLite)
  ไม่มี: ขอบเขตน้ำท่วมจากดาวเทียมรายวันย้อนหลัง และความลึกน้ำท่วม
         -> จึงไม่ยืนยันว่า "ท่วม/ไม่ท่วม" หรือ "ท่วมสูงกี่เมตร"
"""

from datetime import date, datetime, timedelta, timezone

from rainfall import get_rainfall_on_date, is_high_rain, RAIN_CAVEAT, RAIN_RISK_NOTE
from history_store import get_nearest_station_on_date, get_available_range
from thaiwater_station import get_valid_waterlevel, get_valid_critical_level

_BKK = timezone(timedelta(hours=7))

NO_SATELLITE_NOTE = ("ℹ️ ระบบยังไม่มีข้อมูลขอบเขตน้ำท่วมจากดาวเทียมรายวันย้อนหลัง และไม่มีข้อมูลความลึกน้ำท่วม "
                     "จึงยืนยันไม่ได้ว่าวันนั้นท่วมหรือไม่ และท่วมสูงกี่เมตร")


def parse_date_safe(date_str, today=None):
    """YYYY-MM-DD -> date  (แปลงปี พ.ศ. เป็น ค.ศ. ให้ถ้าปี > 2400) คืน None ถ้าอ่านไม่ได้"""
    if not date_str:
        return None
    try:
        d = datetime.strptime(str(date_str).strip().strip('"\''), "%Y-%m-%d").date()
    except ValueError:
        return None
    if d.year > 2400:
        try:
            d = d.replace(year=d.year - 543)
        except ValueError:
            return None
    return d


def extract_place_with_gemini(text):
    """สกัดชื่อสถานที่จากข้อความ (ใช้ Gemini ตัวเดียวกับที่ rag_query ตั้งค่าไว้) คืน None ถ้าไม่มี"""
    from rag_query import genai, INTENT_MODEL  # import ตอนเรียกใช้ กัน circular import

    prompt = f"""จากข้อความต่อไปนี้ ให้สกัดเฉพาะ "ชื่อสถานที่" (จังหวัด อำเภอ หรือตำบล) ที่ผู้ใช้ถามถึง
ตอบเป็นชื่อสถานที่เท่านั้น เช่น "จังหวัดสกลนคร" ถ้าไม่มีชื่อสถานที่ในข้อความให้ตอบว่า NONE
ห้ามมีคำอธิบายอื่น

ข้อความ: "{text}"
คำตอบ:"""
    try:
        model = genai.GenerativeModel(INTENT_MODEL)
        resp = model.generate_content(prompt, generation_config={"temperature": 0.0})
        place = resp.text.strip().strip('"\'')
        return None if (not place or place.upper() == "NONE") else place
    except Exception as e:
        print(f"[warn] extract_place ล้มเหลว: {e}")
        return None


def _format_station_line(st):
    level = get_valid_waterlevel({"waterlevel_msl": st.get("waterlevel_msl")})
    crit = get_valid_critical_level({"critical_level_msl": st.get("critical_level_msl")})
    if level is None:
        return (f"📍 สถานีวัดน้ำใกล้สุด {st['station_name']} (ห่าง {st['distance_km']} กม.): "
                f"ค่าที่บันทึกไว้ผิดปกติ ใช้ไม่ได้")
    text = (f"📍 สถานีวัดน้ำใกล้สุด {st['station_name']} (ห่าง {st['distance_km']} กม.): "
            f"ระดับน้ำ {level} ม.รทก. ณ {st.get('waterlevel_datetime') or 'ไม่ทราบเวลา'}")
    if crit is not None:
        text += f" (เกณฑ์วิกฤต {crit} ม.รทก.)"
    return text + "\n   (สถานะของแม่น้ำที่สถานีนี้เท่านั้น ไม่ได้บอกว่าพื้นที่รอบข้างท่วมหรือไม่)"


def answer_historical(question, *, extract_date=None, extract_place=None, geocode=None,
                      rain_fn=get_rainfall_on_date, station_fn=get_nearest_station_on_date,
                      range_fn=get_available_range, today=None):
    if extract_date is None:
        from rag_query import extract_date_from_text as extract_date
    if extract_place is None:
        extract_place = extract_place_with_gemini
    if geocode is None:
        from location_parser import try_geocode_address as geocode

    today = today or datetime.now(_BKK).date()

    day = parse_date_safe(extract_date(question))
    if day is None:
        return "สายธารอยากช่วยหาข้อมูลย้อนหลังให้นะคะ ช่วยระบุวันที่ให้ชัดเจนอีกนิดได้ไหมคะ เช่น 21 กันยายน 2569"
    if day > today:
        return f"วันที่ {day.isoformat()} ยังมาไม่ถึงเลยค่ะ ถ้าอยากรู้วันที่ผ่านมา ลองระบุวันที่ในอดีตนะคะ"

    place = extract_place(question)
    if not place:
        return "ช่วยบอกด้วยนะคะว่าต้องการดูพื้นที่ไหน เช่น ชื่อจังหวัดหรืออำเภอ พร้อมวันที่ที่อยากทราบ"

    coords = geocode(place)
    if not coords:
        return f"หาตำแหน่งของ '{place}' ไม่เจอค่ะ ลองระบุชื่อจังหวัด/อำเภอให้ชัดเจนขึ้นนะคะ"
    lat, lng = coords

    lines = [f"📅 ข้อมูลย้อนหลังวันที่ {day.isoformat()} บริเวณ {place}"]

    # --- ฝนรายวัน ---
    try:
        rain = rain_fn(lat, lng, day)
    except Exception as e:
        print(f"[warn] rainfall ย้อนหลังล้มเหลว: {e}")
        rain = None
    if rain and rain.get("status") == "ok":
        lines.append(f"🌧️ ฝนรวมทั้งวัน (ณ จุดกึ่งกลางพื้นที่ที่ระบุ): {rain['rain_mm']} มม. ({rain['level']}) {RAIN_CAVEAT}")
        if is_high_rain(rain["level"]):
            lines.append(RAIN_RISK_NOTE)
    else:
        lines.append("🌧️ ไม่สามารถดึงข้อมูลฝนของวันนั้นได้ในขณะนี้")

    # --- ระดับน้ำสถานี (เฉพาะวันที่ระบบเก็บไว้) ---
    st = station_fn(lat, lng, day.isoformat())
    if st:
        lines.append(_format_station_line(st))
    else:
        first, last = range_fn()
        if first:
            lines.append(f"📍 ระบบไม่มีข้อมูลระดับน้ำสถานีของวันนั้น (เริ่มเก็บข้อมูลรายวันตั้งแต่ {first} ถึง {last})")
        else:
            lines.append("📍 ระบบเพิ่งเริ่มเก็บข้อมูลระดับน้ำรายวัน จึงยังไม่มีข้อมูลย้อนหลังของสถานี")

    lines.append("")
    lines.append(NO_SATELLITE_NOTE)
    return "\n".join(lines)
