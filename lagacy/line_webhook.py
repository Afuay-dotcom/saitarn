"""
line_webhook.py
================
Server ที่ LINE จะยิง HTTP POST มาหาทุกครั้งที่มีคนทัก OA ของเรา
(ไม่ว่าจะพิมพ์ข้อความ หรือแชร์พิกัด)

ก่อนรัน ต้องติดตั้งเพิ่ม:
    pip install fastapi uvicorn

และตั้งค่าใน .env เพิ่ม:
    LINE_CHANNEL_ACCESS_TOKEN=...
    LINE_CHANNEL_SECRET=...

วิธีรันบนเครื่อง dev (localhost):
    uvicorn line_webhook:app --reload --port 8000

จากนั้นต้องเปิด tunnel ให้ LINE เข้าถึง localhost ได้ (เช่นผ่าน ngrok)
แล้วเอา URL ที่ได้ (เช่น https://xxxx.ngrok-free.app/callback) ไปใส่ใน
LINE Developers Console -> Messaging API -> Webhook URL
"""

import os
import hmac
import hashlib
import base64

from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
import requests

from message_handler import handle_message

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

app = FastAPI()


# ---------------------------------------------------------------------------
# ยืนยันว่า request นี้มาจาก LINE จริง (ไม่ใช่คนอื่นปลอมมายิง webhook เล่น)
# ---------------------------------------------------------------------------

def verify_line_signature(body: bytes, signature: str) -> bool:
    """
    LINE จะแนบ header 'X-Line-Signature' มาด้วยทุก request
    เราต้องคำนวณ HMAC-SHA256 ของ body ด้วย Channel Secret แล้วเทียบว่าตรงกันไหม
    ถ้าไม่ตรง = อาจไม่ใช่ request จาก LINE จริง ควรปฏิเสธ
    """
    hash_digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    expected_signature = base64.b64encode(hash_digest).decode("utf-8")

    return hmac.compare_digest(expected_signature, signature)


# ---------------------------------------------------------------------------
# ส่งข้อความตอบกลับไปยัง LINE
# ---------------------------------------------------------------------------

def reply_to_line(reply_token: str, text: str):
    """
    เรียก LINE Reply API เพื่อตอบกลับข้อความ
    (reply_token ใช้ได้แค่ครั้งเดียว และมีเวลาหมดอายุสั้นมาก ต้องรีบตอบ)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }

    resp = requests.post(LINE_REPLY_URL, headers=headers, json=payload, timeout=10)

    if resp.status_code != 200:
        print(f"[error] LINE reply ล้มเหลว: {resp.status_code} {resp.text}")


# ---------------------------------------------------------------------------
# Endpoint หลักที่ LINE ยิงมาหา
# ---------------------------------------------------------------------------

@app.post("/callback")
async def callback(request: Request):
    body_bytes = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not verify_line_signature(body_bytes, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    events = payload.get("events", [])

    for event in events:
        event_type = event.get("type")

        # เราสนใจแค่ตอนมีข้อความส่งเข้ามา (message event)
        if event_type != "message":
            continue

        reply_token = event.get("replyToken")
        message = event.get("message", {})
        message_type = message.get("type")

        try:
            if message_type == "text":
                user_text = message.get("text", "")
                reply_text = handle_message("text", text=user_text)

            elif message_type == "location":
                lat = message.get("latitude")
                lng = message.get("longitude")
                print(f"[info] ได้รับพิกัดจริงจาก LINE: lat={lat}, lng={lng}")  # log ไว้ debug ได้แม่นยำ
                reply_text = handle_message("location", lat=lat, lng=lng)

            else:
                reply_text = "ขออภัยค่ะ ระบบรองรับเฉพาะข้อความและการแชร์พิกัดเท่านั้น"

        except Exception as e:
            # กันไม่ให้ webhook ทั้งตัวล่มเพราะ error จุดใดจุดหนึ่ง
            print(f"[error] handle_message ล้มเหลว: {e}")
            reply_text = "ขออภัยค่ะ ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง"

        reply_to_line(reply_token, reply_text)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Endpoint เช็คว่า server ยังทำงานอยู่ (เอาไว้เทสง่ายๆ ผ่าน browser)
# ---------------------------------------------------------------------------

@app.get("/")
async def health_check():
    return {"status": "server กำลังทำงานอยู่ค่ะ"}