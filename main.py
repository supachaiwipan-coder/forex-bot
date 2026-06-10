from flask import Flask
import threading
import time
import os
import requests

app = Flask(__name__)

# ใส่เลข Chat ID ของพี่เรียบร้อยครับ
MY_CHAT_ID = -1003911767447

@app.route('/')
def home():
    return "Forex Bot Running 🚀"

# ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนเข้า Telegram
def send_telegram_message(token, chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("ส่งแจ้งเตือนเข้า Telegram สำเร็จแล้วครับพี่!")
        else:
            print(f"ส่งไม่สำเร็จ รหัสสถานะ: {response.status_code}")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่ง Telegram: {e}")

def bot():
    # ดึงค่า TOKEN จาก Environment Variables ใน Render ที่พี่ตั้งค่าไว้
    token = os.environ.get("TOKEN")
    
    while True:
        print("Bot running...")
        
        if token:
            # ข้อความที่ต้องการให้เด้งเตือนในกลุ่ม (พี่เปลี่ยนข้อความตรงนี้ได้ตามต้องการเลยครับ)
            message_text = "🔔 แจ้งเตือนอัตโนมัติ: บอท Forex ของพี่ทำงานปกติครับ!"
            
            # สั่งให้ส่งข้อความเข้ากลุ่ม ทุกๆ 1 นาที (60 วินาที)
            send_telegram_message(token, MY_CHAT_ID, message_text)
        else:
            print("❌ ไม่พบ TOKEN ในระบบ Render ครับพี่ กรุณาเช็คหน้า Environment Variables")
            
        time.sleep(60)

# เริ่มรันบอทใน Background Thread
threading.Thread(target=bot, daemon=True).start()

if __name__ == "__main__":
    # รันเว็บ Flask สำหรับเปิด Server บน Render
    app.run(host="0.0.0.0", port=10000)
