"""
export_thaiwater_snapshot.py
==============================
ดึงข้อมูลสถานีวัดระดับน้ำทั้งหมดจาก Thaiwater แล้วบันทึกเป็นไฟล์ CSV
เพื่อเก็บเป็น snapshot ณ วันที่ดึงข้อมูล (เนื่องจาก Thaiwater ไม่มี public API
อย่างเป็นทางการ ข้อมูลอาจเปลี่ยนแปลงหรือ endpoint อาจถูกปิดได้ในอนาคต
จึงควรมีไฟล์สำรองไว้ใช้อ้างอิงประกอบเล่มโครงงาน)

วิธีใช้:
    python export_thaiwater_snapshot.py

ผลลัพธ์: ไฟล์ thaiwater_snapshot_YYYYMMDD.csv ในโฟลเดอร์เดียวกัน
"""

import csv
from datetime import datetime

from thaiwater_station import fetch_all_stations


# fields ที่จะบันทึกลง CSV (เลือกเฉพาะที่เกี่ยวข้องกับการใช้งานจริงในโปรเจกต์)
CSV_FIELDS = [
    "station_id",
    "station_name_th",
    "agency_name_th",
    "tele_station_lat",
    "tele_station_long",
    "river_name",
    "waterlevel_datetime",
    "waterlevel_msl",
    "diff_wl_bank",
    "diff_wl_bank_text",
    "critical_level_m",
    "critical_level_msl",
    "ground_level",
    "left_bank",
    "right_bank",
    "min_bank",
]


def flatten_station_record(record: dict) -> dict:
    """
    แปลง record ดิบ (ที่มีโครงสร้างซ้อนกันหลายชั้น) ให้เป็น dict แบนราบ
    พร้อมสำหรับเขียนลง CSV แถวเดียว
    """
    station_info = record.get("station", {})
    agency_info = record.get("agency", {})

    station_name = station_info.get("tele_station_name", {})
    station_name_th = (
        station_name.get("th") if isinstance(station_name, dict) else None
    ) or ""

    agency_name = agency_info.get("agency_name", {})
    agency_name_th = (
        agency_name.get("th") if isinstance(agency_name, dict) else None
    ) or ""

    return {
        "station_id": station_info.get("id"),
        "station_name_th": station_name_th.strip(),
        "agency_name_th": agency_name_th.strip(),
        "tele_station_lat": station_info.get("tele_station_lat"),
        "tele_station_long": station_info.get("tele_station_long"),
        "river_name": record.get("river_name"),
        "waterlevel_datetime": record.get("waterlevel_datetime"),
        "waterlevel_msl": record.get("waterlevel_msl"),
        "diff_wl_bank": record.get("diff_wl_bank"),
        "diff_wl_bank_text": record.get("diff_wl_bank_text"),
        "critical_level_m": station_info.get("critical_level_m"),
        "critical_level_msl": station_info.get("critical_level_msl"),
        "ground_level": station_info.get("ground_level"),
        "left_bank": station_info.get("left_bank"),
        "right_bank": station_info.get("right_bank"),
        "min_bank": station_info.get("min_bank"),
    }


def export_to_csv():
    print("กำลังดึงข้อมูลสถานีทั้งหมดจาก Thaiwater...")
    all_stations = fetch_all_stations()
    print(f"ดึงมาได้ทั้งหมด {len(all_stations)} สถานี")

    today_str = datetime.now().strftime("%Y%m%d")
    output_filename = f"thaiwater_snapshot_{today_str}.csv"

    with open(output_filename, "w", newline="", encoding="utf-8-sig") as f:
        # utf-8-sig เพื่อให้ Excel เปิดไฟล์แล้วอ่านภาษาไทยได้ถูกต้อง ไม่เพี้ยน
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for record in all_stations:
            row = flatten_station_record(record)
            writer.writerow(row)

    print(f"\nบันทึกไฟล์สำเร็จ: {output_filename}")
    print(f"จำนวนแถวทั้งหมด: {len(all_stations)}")


if __name__ == "__main__":
    export_to_csv()
