"""
scan_diff_wl_bank_anomalies.py
================================
สแกนสถานีวัดน้ำทั้งหมดจาก Thaiwater เพื่อหาว่ามีกี่สถานีที่เข้าข่ายบั๊ก
"diff_wl_bank เท่ากับ waterlevel_msl เป๊ะ" (ซึ่งเป็นสัญญาณว่าค่าที่ควรจะเป็น
ผลต่างจากตลิ่ง กลับถูกแทนที่ด้วยค่าระดับน้ำดิบเฉยๆ)

จุดประสงค์หลัก: ทดสอบสมมติฐานที่สังเกตได้ระหว่างทดสอบจริงว่า
"สถานีที่มี critical_level_msl (เกณฑ์วิกฤต) เท่านั้นที่เจอปัญหานี้
ส่วนสถานีที่ไม่มีเกณฑ์วิกฤตไม่เคยเจอปัญหาเลย"
โดยเช็คด้วยข้อมูลทั้งหมด ไม่ใช่แค่สังเกตจากตัวอย่างไม่กี่จุด
"""

from thaiwater_station import fetch_all_stations


def scan_anomalies():
    print("กำลังดึงข้อมูลสถานีทั้งหมด...")
    all_stations = fetch_all_stations()
    total = len(all_stations)
    print(f"ดึงมาได้ทั้งหมด {total} สถานี\n")

    anomaly_with_critical = 0
    anomaly_without_critical = 0
    normal_with_critical = 0
    normal_without_critical = 0

    anomaly_agency_count = {}
    anomaly_examples = []

    for record in all_stations:
        station_info = record.get("station", {})
        diff_value = record.get("diff_wl_bank")
        current_msl = record.get("waterlevel_msl")
        critical_msl = station_info.get("critical_level_msl")

        has_critical = critical_msl is not None

        is_anomaly = False
        if diff_value is not None and current_msl is not None:
            try:
                is_anomaly = abs(float(diff_value) - float(current_msl)) < 0.01
            except (TypeError, ValueError):
                pass

        if is_anomaly and has_critical:
            anomaly_with_critical += 1
        elif is_anomaly and not has_critical:
            anomaly_without_critical += 1
        elif not is_anomaly and has_critical:
            normal_with_critical += 1
        else:
            normal_without_critical += 1

        if is_anomaly:
            agency_info = record.get("agency", {})
            agency_name = agency_info.get("agency_name", {})
            agency_th = (
                agency_name.get("th") if isinstance(agency_name, dict) else None
            ) or "ไม่ทราบหน่วยงาน"
            agency_th = agency_th.strip()

            anomaly_agency_count[agency_th] = anomaly_agency_count.get(agency_th, 0) + 1

            if len(anomaly_examples) < 5:
                station_name = station_info.get("tele_station_name", {})
                name_th = (
                    station_name.get("th") if isinstance(station_name, dict) else None
                ) or "ไม่ทราบชื่อ"
                anomaly_examples.append({
                    "station_id": station_info.get("id"),
                    "name": name_th.strip(),
                    "agency": agency_th,
                    "value": diff_value,
                })

    total_anomaly = anomaly_with_critical + anomaly_without_critical

    print("=== ผลการสแกนหาสถานีที่มีปัญหา (diff_wl_bank == waterlevel_msl) ===")
    print(f"พบสถานีที่มีปัญหาทั้งหมด: {total_anomaly}/{total} ({total_anomaly/total*100:.2f}%)\n")

    print("=== ทดสอบสมมติฐาน: ปัญหาเกี่ยวข้องกับการมี critical_level_msl หรือไม่ ===")
    print(f"มีปัญหา + มี critical_level_msl:     {anomaly_with_critical}")
    print(f"มีปัญหา + ไม่มี critical_level_msl:   {anomaly_without_critical}")
    print(f"ปกติ + มี critical_level_msl:        {normal_with_critical}")
    print(f"ปกติ + ไม่มี critical_level_msl:      {normal_without_critical}")

    if total_anomaly > 0:
        pct_anomaly_has_critical = anomaly_with_critical / total_anomaly * 100
        print(f"\nสัดส่วนสถานีที่มีปัญหา ซึ่งมี critical_level_msl ด้วย: {pct_anomaly_has_critical:.1f}%")
        if pct_anomaly_has_critical > 90:
            print(">> สนับสนุนสมมติฐาน: ปัญหานี้เกิดเกือบเฉพาะกับสถานีที่มี critical_level_msl จริง")
        elif pct_anomaly_has_critical < 10:
            print(">> ไม่สนับสนุนสมมติฐาน: ปัญหาเกิดกับสถานีที่ไม่มี critical_level_msl เป็นส่วนใหญ่")
        else:
            print(">> ผลลัพธ์ไม่ชัดเจน ไม่สามารถสรุปความสัมพันธ์ได้แน่นอน")

    print("\n=== แยกตามหน่วยงานที่มีปัญหา ===")
    for agency, count in sorted(anomaly_agency_count.items(), key=lambda x: -x[1]):
        print(f"  {agency}: {count} สถานี")

    print("\n=== ตัวอย่างสถานีที่มีปัญหา (สูงสุด 5 รายการ) ===")
    for ex in anomaly_examples:
        print(f"  {ex['name']} (id={ex['station_id']}, หน่วยงาน={ex['agency']}, ค่า={ex['value']})")


if __name__ == "__main__":
    scan_anomalies()
