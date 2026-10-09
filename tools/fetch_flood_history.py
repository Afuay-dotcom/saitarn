"""
fetch_flood_history.py
=======================
ดึงข้อมูลพื้นที่น้ำท่วมจาก GISTDA "ครบทุกหน้า" แล้วบันทึกเป็นไฟล์ GeoJSON

ทำไมต้องมี: ผลทดสอบสกลนครก่อนหน้านี้ได้ numberMatched=94 แต่ numberReturned=10
แปลว่า API ส่งกลับมาทีละ 10 รายการ ถ้าดึงแค่หน้าเดียวจะได้ไม่ครบ

ใช้ได้กับ endpoint:
    /features/flood-freq     (พื้นที่น้ำท่วมซ้ำซาก - ข้อมูลสรุปหลายปี)
    /features/flood/30days   (น้ำท่วมย้อนหลัง 30 วัน)

หมายเหตุ: ชื่อ parameter "limit"/"offset" เดาตามมาตรฐาน OGC API Features
(response มี numberMatched/numberReturned ตามมาตรฐานนี้) ยังไม่ได้ยืนยันกับเอกสาร
GISTDA ถ้า API ไม่รองรับ สคริปต์จะแจ้งเตือนแล้วหยุด ไม่วนซ้ำไม่จบ

วิธีใช้:
    python fetch_flood_history.py
"""

import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api-gateway.gistda.or.th/api/2.0/resources"

# ---- แก้ตรงนี้ได้ ----
ENDPOINT = "/features/flood/30days"
BBOX = "103.5,16.8,104.3,17.6"             # จังหวัดสกลนคร
PAGE_SIZE = 100
MAX_PAGES = 50                             # กันวนซ้ำไม่จบ (สูงสุด 5,000 รายการ)


def fetch_all_features(url, base_params, headers, page_size=PAGE_SIZE,
                       max_pages=MAX_PAGES, get=requests.get):
    """
    ดึงทีละหน้าด้วย limit/offset จนครบตาม numberMatched
    คืนค่า (features ทั้งหมด, numberMatched ตามที่ API บอก)
    พารามิเตอร์ get ไว้ให้ทดสอบโดยไม่ต้องยิง API จริง
    """
    all_features = []
    seen_ids = set()
    number_matched = None
    offset = 0

    for _ in range(max_pages):
        params = dict(base_params, limit=page_size, offset=offset)
        resp = get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if number_matched is None:
            number_matched = data.get("numberMatched")

        features = data.get("features", [])
        if not features:
            break

        # กันกรณี API ไม่สนใจ offset แล้วส่งหน้าแรกซ้ำมาเรื่อยๆ
        new_count = 0
        for f in features:
            fid = f.get("id") or json.dumps(f.get("geometry"), sort_keys=True)[:200]
            if fid not in seen_ids:
                seen_ids.add(fid)
                all_features.append(f)
                new_count += 1

        if new_count == 0:
            print("[warn] หน้าถัดไปได้ข้อมูลซ้ำทั้งหมด น่าจะไม่รองรับ offset จึงหยุด")
            break

        offset += len(features)
        if number_matched is not None and len(all_features) >= number_matched:
            break

    return all_features, number_matched


def main():
    api_key = os.getenv("GISTDA_API_KEY")
    if not api_key:
        raise RuntimeError("ไม่พบ GISTDA_API_KEY ใน .env")

    headers = {"API-Key": api_key}
    url = BASE_URL + ENDPOINT

    print(f"กำลังดึง {ENDPOINT} bbox={BBOX} ...")
    features, matched = fetch_all_features(url, {"bbox": BBOX}, headers)

    print(f"API บอกว่ามีทั้งหมด (numberMatched): {matched}")
    print(f"ดึงมาได้จริง: {len(features)} รายการ")
    if matched is not None and len(features) < matched:
        print("[warn] ดึงได้ไม่ครบ ตรวจสอบชื่อ parameter limit/offset ในหน้า Swagger")

    if features:
        props = features[0].get("properties", {})
        print("\nfield ใน properties ของรายการแรก:")
        for key in props:
            print(f"  - {key}")

    today = datetime.now().strftime("%Y%m%d")
    name = ENDPOINT.strip("/").replace("/", "_")
    out_file = f"gistda_{name}_{today}.geojson"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features},
                  f, ensure_ascii=False)
    print(f"\nบันทึกไฟล์แล้ว: {out_file}")


if __name__ == "__main__":
    main()
