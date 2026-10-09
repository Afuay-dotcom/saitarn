"""test_history.py — เทสต์ฝนสะสม / SQLite / คำถามย้อนหลัง โดยไม่ยิง API จริง (python test_history.py)"""
import os, sys, tempfile, types
from datetime import date, datetime

# stub โมดูลหนักที่ไม่จำเป็นต่อเทสต์ (เครื่องจริงใช้ตัวจริง)
for name in ["dotenv", "google", "google.generativeai", "pinecone", "shapely", "shapely.geometry", "pypdf"]:
    if name not in sys.modules:
        try: __import__(name)
        except ImportError: sys.modules[name] = types.ModuleType(name)
sys.modules["dotenv"].load_dotenv = getattr(sys.modules["dotenv"], "load_dotenv", lambda *a, **k: None)
if not hasattr(sys.modules["shapely.geometry"], "Point"):
    sys.modules["shapely.geometry"].Point = lambda *a: None
    sys.modules["shapely.geometry"].shape = lambda d: None
os.environ["GISTDA_API_KEY"] = "x"

import rainfall as rf, history_store as hs, historical as hi, thaiwater_station as ts

class Resp:
    def __init__(s, d): s.d = d
    def raise_for_status(s): pass
    def json(s): return s.d

def hourly_get(url, params=None, timeout=None):
    # 4 วัน x 24 ชม. เริ่ม 2026-10-05T00:00 ฝน 1 มม./ชม. ทุกชั่วโมง; ชั่วโมงเดียวเป็น None
    from datetime import timedelta
    t0 = datetime(2026, 10, 5); times, vals = [], []
    for i in range(96):
        times.append((t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M")); vals.append(1.0)
    vals[50] = None
    return Resp({"hourly": {"time": times, "precipitation": vals}})

# ---------- rainfall ----------
def test_classify():
    c = rf.classify_rain_24h
    assert c(0) == "ไม่มีฝน" and c(0.1) == "ฝนเล็กน้อย" and c(10.0) == "ฝนเล็กน้อย" and c(10.1) == "ฝนปานกลาง"
    assert c(35.0) == "ฝนปานกลาง" and c(35.1) == "ฝนหนัก" and c(90.0) == "ฝนหนัก" and c(90.1) == "ฝนหนักมาก"
    assert c(None) is None

def test_recent_rain_excludes_future_hours():
    now = datetime(2026, 10, 8, 12, 0)   # ชั่วโมงที่ index 84 ; ข้อมูลหลังจากนี้ต้องไม่นับ
    r = rf.get_recent_rainfall(17.0, 104.0, get=hourly_get, now=now)
    assert r["rain_24h_mm"] == 24.0           # 24 ชั่วโมง (ไม่มีชั่วโมงที่เป็น None ในช่วงนี้)
    assert r["rain_72h_mm"] == 71.0           # 72 ชั่วโมง ลบชั่วโมงที่เป็น None 1 ชั่วโมง
    assert r["level_24h"] == "ฝนปานกลาง"

def test_recent_rain_no_data():
    get = lambda *a, **k: Resp({"hourly": {"time": [], "precipitation": []}})
    assert rf.get_recent_rainfall(1, 1, get=get) is None

def test_rain_on_date_routing():
    calls = []
    def get(url, params=None, timeout=None):
        calls.append((url, params))
        day = params.get("start_date") or "2026-10-06"
        return Resp({"daily": {"time": [day], "precipitation_sum": [95.4]}})
    today = date(2026, 10, 8)
    r1 = rf.get_rainfall_on_date(1, 1, date(2026, 10, 6), get=get, today=today)
    assert calls[-1][0] == rf.FORECAST_URL and calls[-1][1]["past_days"] == 2 and r1["level"] == "ฝนหนักมาก"
    r2 = rf.get_rainfall_on_date(1, 1, date(2026, 9, 21), get=get, today=today)
    assert calls[-1][0] == rf.ARCHIVE_URL and calls[-1][1]["start_date"] == "2026-09-21" and r2["status"] == "ok"
    assert rf.get_rainfall_on_date(1, 1, date(2026, 10, 9), get=get, today=today)["status"] == "future"
    nodata = lambda *a, **k: Resp({"daily": {"time": ["2026-09-21"], "precipitation_sum": [None]}})
    assert rf.get_rainfall_on_date(1, 1, date(2026, 9, 21), get=nodata, today=today)["status"] == "no_data"

# ---------- SQLite ----------
def rec(i, lat, lng, wl, crit=None, name="สถานี"):
    return {"station": {"id": i, "tele_station_name": {"th": f"{name}{i}"}, "tele_station_lat": lat,
                        "tele_station_long": lng, "critical_level_msl": crit},
            "agency": {"agency_name": {"th": "กรมชล"}}, "waterlevel_msl": wl, "waterlevel_datetime": "2026-09-21 07:00"}

def test_store():
    db = os.path.join(tempfile.mkdtemp(), "t.db")
    assert hs.get_available_range(db) == (None, None)
    recs = [rec(1, 17.1, 104.1, 150.2, 152.0), rec(2, 13.7, 100.5, 1.1)]
    assert hs.save_station_snapshot(recs, "2026-09-21", db) == 2
    hs.save_station_snapshot(recs, "2026-09-21", db)                    # รันซ้ำวันเดิม ไม่ซ้ำแถว
    assert hs.get_available_range(db) == ("2026-09-21", "2026-09-21")
    n = hs.get_nearest_station_on_date(17.0, 104.0, "2026-09-21", db_path=db)
    assert n["station_id"] == 1 and n["distance_km"] < 20
    assert hs.get_nearest_station_on_date(17.0, 104.0, "2026-09-20", db_path=db) is None      # ไม่มี snapshot วันนั้น
    assert hs.get_nearest_station_on_date(5.0, 100.0, "2026-09-21", max_km=50, db_path=db) is None  # ไกลเกินไป

# ---------- historical ----------
def test_parse_date():
    assert hi.parse_date_safe("2026-09-21") == date(2026, 9, 21)
    assert hi.parse_date_safe("2569-09-21") == date(2026, 9, 21)     # ปี พ.ศ.
    assert hi.parse_date_safe("เมื่อวาน") is None and hi.parse_date_safe(None) is None
    assert hi.parse_date_safe("2026-13-40") is None

def run(q="วันที่ 21 กันยายน สกลนครท่วมไหม ท่วมสูงกี่เมตร", **kw):
    base = dict(extract_date=lambda t: "2026-09-21", extract_place=lambda t: "จังหวัดสกลนคร",
                geocode=lambda p: (17.15, 104.14),
                rain_fn=lambda la, ln, d: {"status": "ok", "rain_mm": 95.4, "level": "ฝนหนักมาก"},
                station_fn=lambda la, ln, d: None, range_fn=lambda: (None, None), today=date(2026, 10, 8))
    base.update(kw); return hi.answer_historical(q, **base)

def test_historical_flow():
    out = run()
    assert "95.4 มม." in out and "ฝนหนักมาก" in out and "ไม่ได้ยืนยันว่าท่วมจริง" in out
    assert "ยืนยันไม่ได้ว่าวันนั้นท่วมหรือไม่" in out and "เพิ่งเริ่มเก็บ" in out
    st = {"station_name": "สกลนคร", "distance_km": 3.2, "waterlevel_msl": 150.2,
          "critical_level_msl": 152.0, "waterlevel_datetime": "2026-09-21 07:00"}
    out = run(station_fn=lambda la, ln, d: st)
    assert "150.2 ม.รทก." in out and "เกณฑ์วิกฤต 152.0" in out and "ไม่ได้บอกว่าพื้นที่รอบข้างท่วม" in out
    out = run(station_fn=lambda la, ln, d: None, range_fn=lambda: ("2026-10-01", "2026-10-07"))
    assert "2026-10-01" in out and "2026-10-07" in out

def test_historical_edge_cases():
    assert "ระบุวันที่" in run(extract_date=lambda t: None)
    assert "ยังมาไม่ถึง" in run(extract_date=lambda t: "2026-12-01")
    assert "ต้องการดูพื้นที่ไหน" in run(extract_place=lambda t: None)
    assert "หาตำแหน่ง" in run(geocode=lambda p: None)
    boom = lambda *a: (_ for _ in ()).throw(RuntimeError("down"))
    assert "ไม่สามารถดึงข้อมูลฝนของวันนั้นได้" in run(rain_fn=boom)

def test_station_bad_values_not_shown():
    bad = {"station_name": "วัดศรัทธาธรรม", "distance_km": 1.0, "waterlevel_msl": 32765.9,
           "critical_level_msl": 0, "waterlevel_datetime": "x"}
    out = run(station_fn=lambda *a: bad)
    assert "32765" not in out and "ผิดปกติ" in out

# ---------- handle_location ทั้งก้อน ----------
def test_handle_location_message():
    rq = types.ModuleType("rag_query")
    for n in ["answer_question", "classify_intent", "chat_naturally", "extract_date_from_text"]: setattr(rq, n, lambda *a, **k: "")
    rq.genai = None; rq.INTENT_MODEL = "x"
    lp = types.ModuleType("location_parser"); lp.try_parse_safe_location = lambda t: None; lp.try_geocode_address = lambda t: None
    sys.modules["rag_query"], sys.modules["location_parser"] = rq, lp
    import importlib, message_handler as mh; importlib.reload(mh)
    mh.check_flood_risk = lambda la, ln: {"risk": "unknown", "source": "ไม่พบข้อมูล"}
    now = datetime.now(rf._BKK).strftime("%Y-%m-%d %H:%M")
    st = {"station_id": 1, "distance_km": 2.0, "station_name": "ทดสอบ", "agency_name": "กรมชล", "river_name": "น้ำ",
          "waterlevel_datetime": now, "waterlevel_msl": 10.0, "critical_level_msl": 20.0}
    mh.fetch_all_stations = lambda: []; mh.find_nearest_station = lambda *a, **k: [st]
    mh.get_recent_rainfall = lambda la, ln: {"rain_24h_mm": 120.0, "rain_72h_mm": 150.0, "level_24h": "ฝนหนักมาก", "as_of": "x"}
    out = mh.handle_location(13.7, 100.5)
    print("\n----- ตัวอย่างข้อความที่ผู้ใช้จะได้รับ -----\n" + out + "\n---------------------------------------")
    assert "🟢" not in out and "ฝนสะสม 24 ชม." in out and "1784" in out and "ไม่ได้ยืนยันว่าท่วมจริง" in out
    mh.get_recent_rainfall = lambda la, ln: (_ for _ in ()).throw(RuntimeError("x"))
    assert "ฝนสะสม" not in mh.handle_location(13.7, 100.5)          # ฝนล่ม ไม่ทำให้ทั้งข้อความล่ม

if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try: fn(); print("PASS", name)
            except Exception as e:
                import traceback; fails += 1; print("FAIL", name, "->", repr(e)); traceback.print_exc()
    print("\nทั้งหมดผ่าน" if not fails else f"\nล้มเหลว {fails} เทสต์"); sys.exit(1 if fails else 0)
