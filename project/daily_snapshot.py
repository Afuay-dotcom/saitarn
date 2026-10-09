"""
daily_snapshot.py
=================
ดึงสถานี Thaiwater ทั้งหมดแล้วบันทึกลง SQLite ของวันนี้ (รันวันละครั้ง)

รันมือ:   python daily_snapshot.py
อัตโนมัติ: ใน n8n ใช้ Schedule Trigger (วันละครั้ง) -> HTTP Request POST
           http://127.0.0.1:8000/snapshot   (endpoint อยู่ใน process_api.py)
"""

from history_store import save_station_snapshot, get_available_range
from thaiwater_station import fetch_all_stations


def run_snapshot() -> dict:
    stations = fetch_all_stations()
    saved = save_station_snapshot(stations)
    first, last = get_available_range()
    return {"saved_rows": saved, "first_date": first, "last_date": last}


if __name__ == "__main__":
    print(run_snapshot())
