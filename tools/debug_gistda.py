"""
debug_gistda.py — สคริปต์แยกไว้เช็ค raw response จาก GISTDA โดยตรง
ไม่ผ่าน fallback logic ใดๆ เพื่อดูว่าแต่ละ endpoint คืนอะไรมาบ้าง
"""

import os
import requests

GISTDA_API_KEY = os.getenv("GISTDA_API_KEY", "KLkBISIeru1vwT0VopxUurcv6iBYEFkK9IlbyAzpBWEuDNGdGXyKcA1vOdZrgd82")
BASE_URL = "https://api-gateway.gistda.or.th/api/2.0/resources"

# bbox ครอบคลุมทั้งประเทศไทย (lng_min, lat_min, lng_max, lat_max)
bbox = "97.3,5.6,105.7,20.5"  # กรอบใหญ่คลุมทั้งประเทศไทย

endpoints = [
    "/features/flood/1day",
    "/features/flood/3days",
    "/features/flood/7days",
    "/features/flood/30days",
]

headers = {"API-Key": GISTDA_API_KEY}

for path in endpoints:
    url = BASE_URL + path
    resp = requests.get(url, headers=headers, params={"bbox": bbox}, timeout=10)
    print(f"--- {path} ---")
    print("status code:", resp.status_code)
    data = resp.json()
    print("numberMatched:", data.get("numberMatched"))
    print("numberReturned:", data.get("numberReturned"))
    print()