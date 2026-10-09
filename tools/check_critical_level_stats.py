"""
check_critical_level_stats.py
==============================
เช็คว่า field 'critical_level_m' และ 'critical_level_msl' (เกณฑ์ระดับน้ำวิกฤต
ที่หน่วยงานเจ้าของสถานีกำหนดเอง) มีข้อมูลจริงกี่ % ของสถานีทั้งหมด

เหตุผล: ถ้า field นี้ null เกือบทุกสถานี แปลว่าใช้เป็นเกณฑ์หลักในการจำแนก
ความเสี่ยงไม่ได้จริงในทางปฏิบัติ ต้องรู้ตัวเลขนี้ก่อนตัดสินใจออกแบบ logic ต่อ
"""

from thaiwater_station import fetch_all_stations


def analyze_critical_level_coverage():
    print("กำลังดึงข้อมูลสถานีทั้งหมด...")
    all_stations = fetch_all_stations()
    total = len(all_stations)

    print(f"ดึงมาได้ทั้งหมด {total} สถานี (records)\n")

    has_critical_m = 0
    has_critical_msl = 0
    has_either = 0
    has_both = 0

    agency_breakdown = {}  # นับแยกตามหน่วยงาน เผื่อบางหน่วยงานให้ข้อมูลครบกว่า

    for record in all_stations:
        station_info = record.get("station", {})
        critical_m = station_info.get("critical_level_m")
        critical_msl = station_info.get("critical_level_msl")

        agency_info = record.get("agency", {})
        agency_name = agency_info.get("agency_name", {})
        agency_th = agency_name.get("th", "ไม่ทราบหน่วยงาน") if isinstance(agency_name, dict) else "ไม่ทราบหน่วยงาน"

        agency_breakdown.setdefault(agency_th, {"total": 0, "has_critical": 0})
        agency_breakdown[agency_th]["total"] += 1

        m_ok = critical_m is not None
        msl_ok = critical_msl is not None

        if m_ok:
            has_critical_m += 1
        if msl_ok:
            has_critical_msl += 1
        if m_ok or msl_ok:
            has_either += 1
            agency_breakdown[agency_th]["has_critical"] += 1
        if m_ok and msl_ok:
            has_both += 1

    print("=== สรุปภาพรวม ===")
    print(f"มี critical_level_m ไม่เป็น null:   {has_critical_m}/{total} ({has_critical_m/total*100:.1f}%)")
    print(f"มี critical_level_msl ไม่เป็น null: {has_critical_msl}/{total} ({has_critical_msl/total*100:.1f}%)")
    print(f"มีอย่างน้อย 1 ตัว:                  {has_either}/{total} ({has_either/total*100:.1f}%)")
    print(f"มีครบทั้ง 2 ตัว:                     {has_both}/{total} ({has_both/total*100:.1f}%)")

    print("\n=== แยกตามหน่วยงาน (agency) ===")
    for agency, stats in sorted(agency_breakdown.items(), key=lambda x: -x[1]["total"]):
        pct = stats["has_critical"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {agency}: {stats['has_critical']}/{stats['total']} สถานี มีเกณฑ์วิกฤต ({pct:.1f}%)")


if __name__ == "__main__":
    analyze_critical_level_coverage()
