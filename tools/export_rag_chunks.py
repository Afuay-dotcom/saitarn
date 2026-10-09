"""
export_rag_chunks.py
======================
ดึง chunk ทั้งหมด (พร้อมข้อความต้นฉบับ) ที่เก็บอยู่ใน Pinecone มาบันทึกเป็น
ไฟล์ JSON เดียว เพื่อให้อาจารย์/ผู้ตรวจสอบดูเนื้อหา knowledge base ได้โดยตรง
โดยไม่ต้องเข้าไปดูใน Pinecone Console

ใช้วิธี index.list() + index.fetch() ซึ่งเป็นวิธีมาตรฐานของ Pinecone
ในการไล่เอา vector ID ทั้งหมดออกมาก่อน แล้วค่อย fetch metadata ทีละชุด
(ต่างจาก index.query() ที่ออกแบบมาสำหรับค้นหาความใกล้เคียง ไม่ใช่ list
ข้อมูลทั้งหมด)

วิธีใช้:
    python export_rag_chunks.py

ผลลัพธ์: ไฟล์ rag_chunks_export.json ในโฟลเดอร์เดียวกัน
"""

import json
import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "flood-kb-v2"  # ต้องตรงกับชื่อ index จริงที่ใช้อยู่ตอนนี้

if not PINECONE_API_KEY:
    raise RuntimeError("ไม่พบ PINECONE_API_KEY ใน .env กรุณาตรวจสอบไฟล์ .env")


def get_field(obj, key, default=None):
    """
    ดึงค่าจาก obj โดยรองรับทั้งกรณี obj เป็น dict (ใช้ .get()) และกรณี obj
    เป็น response object ของ pinecone (ใช้ attribute access) — เขียนแบบนี้
    เพราะเจอปัญหาจริงว่า pinecone-client คนละเวอร์ชันคืนค่ารูปแบบไม่เหมือนกัน
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def export_chunks():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX_NAME)

    print(f"กำลังเชื่อมต่อ index '{PINECONE_INDEX_NAME}' ...")

    stats = index.describe_index_stats()
    total_vectors = get_field(stats, "total_vector_count", 0)
    print(f"จำนวนเวกเตอร์ทั้งหมดใน index: {total_vectors}")

    all_records = []

    # ไล่ดึง vector ID ทีละชุด (batch) ผ่าน index.list() แล้ว fetch metadata ต่อ
    #
    # หมายเหตุ: pinecone-client บางเวอร์ชันคืนค่าจาก index.list() เป็น list
    # ของ ID string ตรงๆ แต่บางเวอร์ชันคืนเป็น response object ที่มี
    # attribute .vectors (ซึ่งแต่ละตัวเป็น ListItem ที่มี .id) โค้ดด้านล่าง
    # จึงรองรับทั้งสองแบบ กันปัญหาเวอร์ชันไม่ตรงกัน
    for id_batch in index.list():
        if hasattr(id_batch, "vectors"):
            # กรณี response object -> ดึง .id จากแต่ละ ListItem
            ids = [item.id for item in id_batch.vectors]
        elif isinstance(id_batch, str):
            # กรณีคืนมาเป็น string เดี่ยว (ไม่ควรเกิด แต่กันไว้)
            ids = [id_batch]
        else:
            # กรณี list ของ string ตรงๆ ตามเอกสารมาตรฐาน
            ids = list(id_batch)

        if not ids:
            continue

        fetch_result = index.fetch(ids=ids)
        vectors_dict = get_field(fetch_result, "vectors", {}) or {}

        for vector_id, vector_data in vectors_dict.items():
            metadata = get_field(vector_data, "metadata", {}) or {}
            all_records.append({
                "id": vector_id,
                "text": get_field(metadata, "text", ""),
                "source": get_field(metadata, "source", ""),
                "chunk_index": get_field(metadata, "chunk_index"),
            })

        print(f"  ดึงมาแล้ว {len(all_records)} / {total_vectors} chunks...")

    # เรียงตาม chunk_index เพื่อให้อ่านตามลำดับเนื้อหาต้นฉบับได้ง่าย
    all_records.sort(key=lambda r: (r["chunk_index"] is None, r["chunk_index"]))

    output_filename = "rag_chunks_export.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\nบันทึกไฟล์สำเร็จ: {output_filename}")
    print(f"จำนวน chunks ทั้งหมด: {len(all_records)}")


if __name__ == "__main__":
    export_chunks()