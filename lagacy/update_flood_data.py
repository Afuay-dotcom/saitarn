import requests
import json
from datetime import datetime

# 1. ตั้งค่า API Key และ URL
GISTDA_API_KEY = "KLkBISIeru1vwT0VopxUurcv6iBYEFkK9IlbyAzpBWEuDNGdGXyKcA1vOdZrgd82"
# ใช้แบบ 30 วันย้อนหลังเผื่อไว้ก่อน จะได้มีพื้นที่ครอบคลุม
url = f"https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/30days?api_key={GISTDA_API_KEY}"

def update_flood_data():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 เริ่มต้นดาวน์โหลดข้อมูลแผนที่น้ำท่วมจาก GISTDA...")
    
    try:
        # 2. ยิง Request ไปขอข้อมูล
        response = requests.get(url)
        response.raise_for_status() # เช็กว่า Error ไหม
        
        data = response.json()
        
        # 3. บันทึกข้อมูลที่ได้ลงไฟล์ flood_data.geojson
        with open('flood_data.geojson', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("✅ อัปเดตไฟล์ flood_data.geojson สำเร็จแล้ว! พร้อมใช้งานออฟไลน์")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ โหลดข้อมูลไม่สำเร็จ (ปัญหาการเชื่อมต่อ): {e}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดอื่นๆ: {e}")

# สั่งให้ฟังก์ชันทำงาน
if __name__ == "__main__":
    update_flood_data()