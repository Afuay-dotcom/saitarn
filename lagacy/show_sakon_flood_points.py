import os
import requests
from dotenv import load_dotenv

load_dotenv()

GISTDA_API_KEY = os.getenv("GISTDA_API_KEY")
if not GISTDA_API_KEY:
    raise RuntimeError("ไม่พบ GISTDA_API_KEY ในไฟล์ .env")

BASE_URL = "https://api-gateway.gistda.or.th/api/2.0/resources"
bbox = "103.5,16.8,104.3,17.6"  # จังหวัดสกลนคร

headers = {"API-Key": GISTDA_API_KEY}
url = BASE_URL + "/features/flood/30days"

resp = requests.get(url, headers=headers, params={"bbox": bbox}, timeout=30)
data = resp.json()

features = data.get("features", [])
print(f"numberMatched (ทั้งหมดที่ API รายงาน): {data.get('numberMatched')}")
print(f"numberReturned (หน้านี้): {len(features)}\n")

for i, feature in enumerate(features[:10], start=1):
    geom = feature.get("geometry", {})
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    props = feature.get("properties", {})

    try:
        if gtype == "Polygon":
            sample_point = coords[0][0]
        elif gtype == "MultiPolygon":
            sample_point = coords[0][0][0]
        else:
            sample_point = None
    except (IndexError, TypeError):
        sample_point = None

    print(f"--- รายการที่ {i} ---")
    print(f"  properties: {props}")
    if sample_point:
        lng, lat = sample_point[0], sample_point[1]
        print(f"  พิกัดตัวอย่าง: lat={lat}, lng={lng}")
        print(f"  ลิงก์ Google Maps: https://www.google.com/maps?q={lat},{lng}")
    print()