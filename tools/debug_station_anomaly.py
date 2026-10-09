"""
debug_station_anomaly.py
==========================
เจาะดู raw data ของสถานีที่ให้ค่า diff_wl_bank ผิดปกติ (เช่น 176.57 เมตร)
เพื่อหาสาเหตุว่าเกิดจาก field ไหนของ Thaiwater ที่ตั้งค่าผิด/ขาดหาย

วิธีใช้: หาสถานีตามชื่อที่เจอปัญหา (หรือพิกัดใกล้เคียง) แล้ว print
ทุก field ที่เกี่ยวข้องกับการคำนวณระดับน้ำ-ตลิ่งออกมาดูทั้งหมด
"""

from thaiwater_station import fetch_all_stations, find_nearest_station


def inspect_station_raw_data(lat: float, lng: float):
    """
    หาสถานีใกล้พิกัดที่ระบุ แล้ว print raw record ทั้งหมด (ไม่ผ่านการสรุปย่อ)
    เพื่อดู field ที่เกี่ยวกับตลิ่ง/ระดับน้ำ ทุกตัวพร้อมกัน

    สำคัญ: จับคู่ด้วย station_id (ไม่ใช่ชื่อ) เพราะชื่อตำบลในไทยซ้ำกันได้
    ข้ามจังหวัด (เช่น "ตำบลในเมือง" มีได้หลายจังหวัด) การจับคู่ด้วยชื่อ
    เคยทำให้ debug ผิดสถานีมาแล้ว
    """
    print("กำลังดึงข้อมูลสถานีทั้งหมด...")
    all_stations = fetch_all_stations()

    nearest_summary = find_nearest_station(lat, lng, all_stations, max_results=1)

    if not nearest_summary:
        print("ไม่พบสถานีใกล้เคียง")
        return

    target = nearest_summary[0]
    target_id = target["station_id"]
    print(f"สถานีที่ใกล้ที่สุด: {target['station_name']} (station_id={target_id})\n")

    # จับคู่ด้วย station_id เท่านั้น เพื่อความแม่นยำ 100%
    for record in all_stations:
        station_info = record.get("station", {})

        if station_info.get("id") == target_id:
            print("=== Raw fields ที่เกี่ยวกับระดับน้ำ-ตลิ่ง ===")
            print(f"waterlevel_msl:      {record.get('waterlevel_msl')}")
            print(f"diff_wl_bank:        {record.get('diff_wl_bank')}")
            print(f"diff_wl_bank_text:   {record.get('diff_wl_bank_text')}")
            print(f"critical_level_msl:  {station_info.get('critical_level_msl')}")
            print(f"critical_level_m:    {station_info.get('critical_level_m')}")
            print(f"ground_level:        {station_info.get('ground_level')}")
            print(f"left_bank:           {station_info.get('left_bank')}")
            print(f"right_bank:          {station_info.get('right_bank')}")
            print(f"min_bank:            {station_info.get('min_bank')}")
            print(f"offset:              {station_info.get('offset')}")
            print(f"qmax:                {station_info.get('qmax')}")
            break
    else:
        print("ไม่พบ raw record ที่ตรงกับ station_id นี้ (ไม่ควรเกิดขึ้น)")


if __name__ == "__main__":
    # ใส่พิกัดเดียวกับที่ทดสอบตอนแชร์โลเคชันแล้วเจอค่าผิดปกติ
    test_lat = 14.9799   # แก้เป็นพิกัดจริงที่แชร์ไป (นครราชสีมา บริเวณนี้โดยประมาณ)
    test_lng = 102.0977

    inspect_station_raw_data(test_lat, test_lng)