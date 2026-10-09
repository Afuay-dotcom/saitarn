"""
process_api.py
================
Internal API แบบเบาที่สุด สำหรับให้ n8n เรียกใช้เท่านั้น
(ไม่ใช่ endpoint ที่เปิดรับ request จาก LINE โดยตรงแล้ว — n8n ทำหน้าที่นั้นแทน)

สถาปัตยกรรมใหม่:
    LINE -> n8n webhook (รับ request, verify signature, แยกประเภทข้อความ)
         -> เรียก endpoint นี้ (/process) เพื่อประมวลผล
         -> n8n ส่งข้อความตอบกลับไปที่ LINE Reply/Push API เอง

เหตุผลที่ยังใช้ Python endpoint นี้อยู่ (ไม่ย้าย logic ทั้งหมดไป n8n):
logic การประมวลผล (RAG, geocoding, geospatial calculation, intent
classification, sanity check ต่างๆ) มีความซับซ้อนสูงและผ่านการทดสอบมาแล้ว
การเขียนใหม่ทั้งหมดเป็น n8n node จะเสี่ยงเกิดบั๊กใหม่และใช้เวลานานเกินจำเป็น
n8n จึงทำหน้าที่เป็น "ด่านหน้า" (front door) เชื่อมต่อกับ LINE และจัดการ
เรื่อง routing/reply เท่านั้น ส่วนตรรกะหลักยังอยู่ใน Python ตามเดิม

รัน endpoint นี้:
    python -m uvicorn process_api:app --reload --port 8000

(รันที่ port เดิม 8000 ได้เลย เพราะตอนนี้ไม่มีใครจาก LINE ยิงตรงมาที่นี่แล้ว
มีแค่ n8n ที่คุยกับ endpoint นี้ผ่าน localhost เท่านั้น ไม่ต้องเปิด ngrok
ให้ endpoint นี้อีกต่อไป — ngrok จะเปลี่ยนไปเปิดให้ n8n แทน)
"""

from fastapi import FastAPI
from pydantic import BaseModel

from message_handler import handle_message
from daily_snapshot import run_snapshot

app = FastAPI()


class ProcessRequest(BaseModel):
    """
    รูปแบบข้อมูลที่ n8n จะส่งมาให้ endpoint นี้
    message_type: "text" หรือ "location"
    text: ใช้เมื่อ message_type == "text"
    lat, lng: ใช้เมื่อ message_type == "location"
    """
    message_type: str
    text: str | None = None
    lat: float | None = None
    lng: float | None = None


@app.post("/process")
def process(req: ProcessRequest):  # def (ไม่ใช่ async) เพราะข้างในเรียก requests แบบ blocking
    """
    จุดเดียวที่ n8n เรียกใช้ รับ input ที่ n8n แยกประเภทมาให้แล้ว
    ส่งต่อเข้า handle_message() (โมดูลเดิมที่ทดสอบผ่านมาแล้วทั้งหมด)
    คืนค่าเป็นข้อความตอบกลับ ให้ n8n เอาไปส่งต่อที่ LINE Reply/Push API เอง
    """
    try:
        if req.message_type == "text" and req.text:
            reply_text = handle_message("text", text=req.text)

        elif req.message_type == "location" and req.lat is not None and req.lng is not None:
            reply_text = handle_message("location", lat=req.lat, lng=req.lng)

        else:
            reply_text = "ขออภัยค่ะ ระบบรองรับเฉพาะข้อความและการแชร์พิกัดเท่านั้น"

    except Exception as e:
        print(f"[error] process_api ล้มเหลว: {e}")
        reply_text = "ขออภัยค่ะ ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง"

    return {"reply_text": reply_text}


@app.post("/snapshot")
def snapshot():
    """ให้ n8n (Schedule Trigger วันละครั้ง) เรียก เพื่อบันทึกระดับน้ำสถานีของวันนี้ลง SQLite"""
    try:
        return {"ok": True, **run_snapshot()}
    except Exception as e:
        print(f"[error] snapshot ล้มเหลว: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/")
def health_check():
    return {"status": "process_api กำลังทำงานอยู่ค่ะ (รอ n8n เรียกใช้)"}
