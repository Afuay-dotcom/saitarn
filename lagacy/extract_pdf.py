import pdfplumber
import csv

# 1. ฟังก์ชันสำหรับอ่านและทำความสะอาดข้อความจาก PDF
def extract_and_clean_pdf(pdf_path):
    print("กำลังอ่านไฟล์ PDF...")
    all_text = ""
    
    # เปิดไฟล์ PDF
    with pdfplumber.open(pdf_path) as pdf:
        # วนลูปอ่านทีละหน้า
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # ทำความสะอาด: แทนที่การขึ้นบรรทัดใหม่ด้วยช่องว่าง และลบช่องว่างส่วนเกิน
                clean_text = text.replace('\n', ' ').strip()
                all_text += clean_text + " "
                
    return all_text

# 2. ฟังก์ชันหั่นข้อความ (Chunking) เพื่อให้เหมาะกับระบบ RAG
def split_text(text, chunk_size=800):
    print("กำลังหั่นข้อความเป็นท่อนๆ...")
    chunks = []
    # หั่นข้อความตามจำนวนตัวอักษรที่กำหนด (เช่น ท่อนละ 800 ตัวอักษร)
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks

# --- เริ่มการทำงานตรงนี้ ---

# ระบุชื่อไฟล์ PDF ของหนู (ต้องเอาไฟล์ PDF มาวางไว้โฟลเดอร์เดียวกับสคริปต์นี้นะคะ)
file_name = "คู่มือปภ..pdf" 

# เรียกใช้ฟังก์ชัน
raw_text = extract_and_clean_pdf(file_name)
text_chunks = split_text(raw_text, chunk_size=800)

# 3. บันทึกผลลัพธ์ลงไฟล์ CSV เพื่อเตรียมส่งเข้าฐานข้อมูล
output_file = 'cleaned_data.csv'
with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Chunk_ID', 'Content']) # สร้างหัวตาราง
    
    for i, chunk in enumerate(text_chunks):
        writer.writerow([i+1, chunk])

print(f"เสร็จเรียบร้อย! สกัดข้อมูลได้ทั้งหมด {len(text_chunks)} ท่อน บันทึกลง {output_file} แล้วค่ะ")