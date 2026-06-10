from flask import Flask
import threading
import time
import os
import io
import requests
import xml.etree.ElementTree as ET
import yfinance as yf

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# ========================================================
# ⚙️ [ตั้งค่าเลข ID ห้องของพี่]
# ========================================================
MY_CHAT_ID = -1003911767447  

LAST_NEWS_LINK = None
sent_news_links = set()
is_first_run = True  # บอทจะเริ่มนับและส่งเฉพาะข่าวใหม่ที่เกิดขึ้นหลังจากรันบอท

@app.route('/')
def home():
    return "Forex Fast News System Running 🚀"

def escape_html(text):
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    try: 
        requests.post(url, json=payload, timeout=10)
    except Exception as e: 
        print(f"Error: {e}")

# ========================================================
# 📈 1. ฟังก์ชันวาดกราฟเทคนิค
# ========================================================
def generate_and_send_market_report(token):
    print("📈 กำลังส่งรายงานตลาดด่วน...")
    try:
        gold_ticker = yf.Ticker("GC=F")       
        oil_ticker = yf.Ticker("CL=F")        
        dxy_ticker = yf.Ticker("DX-Y.NYB")    

        gold_hist = gold_ticker.history(period="7d", interval="1h")
        oil_hist = oil_ticker.history(period="1d")
        dxy_hist = dxy_ticker.history(period="7d", interval="1h")

        if gold_hist.empty or dxy_hist.empty or oil_hist.empty:
            print("yfinance ไม่มีข้อมูลราคา")
            return

        current_gold = gold_hist['Close'].iloc[-1]
        current_oil = oil_hist['Close'].iloc[-1]
        current_dxy = dxy_hist['Close'].iloc[-1]

        gold_hist['MA20'] = gold_hist['Close'].rolling(window=20).mean()
        ma20_val = gold_hist['MA20'].iloc[-1]

        if current_gold > ma20_val:
            recommendation = "📈 <b>วิเคราะห์เทคนิค (1H):</b> เทรนด์ขาขึ้น (BULLISH)\n🎯 <b>คำแนะนำการเทรด:</b> หาจังหวะเข้าฝั่ง <b>BUY / LONG</b>"
        else:
            recommendation = "📉 <b>วิเคราะห์เทคนิค (1H):</b> เทรนด์ขาลง (BEARISH)\n🎯 <b>คำแนะนำการเทรด:</b> หาจังหวะเข้าฝั่ง <b>SELL / SHORT</b>"

        caption = (
            f"📊 <b>รายงานดัชนีตลาด Real-Time & บทวิเคราะห์</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 <b>ราคาทองคำ (XAU/USD):</b> ${current_gold:,.2f}\n"
            f"🛢️ <b>น้ำมันดิบ WTI:</b> ${current_oil:,.2f} / บาร์เรล\n"
            f"💵 <b>ดัชนีดอลลาร์ (DXY):</b> {current_dxy:,.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{recommendation}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <i>วิเคราะห์อัตโนมัติเบื้องต้น โปรดบริหารความเสี่ยง</i>"
        )

        fig, ax1 = plt.subplots(figsize=(10, 5))
        color = '#d4af37'
        ax1.set_xlabel('Date & Time (Past 7 Days)', fontweight='bold')
        ax1.set_ylabel('Gold Price ($/oz)', color=color, fontweight='bold')
        ax1.plot(gold_hist.index, gold_hist['Close'], color=color, linewidth=2, label='Gold')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle=':', alpha=0.5)

        ax2 = ax1.twinx()
        color = '#1f77b4'
        ax2.set_ylabel('US Dollar Index (DXY)', color=color, fontweight='bold')
        ax2.plot(dxy_hist.index, dxy_hist['Close'], color=color, linewidth=1.5, linestyle='--', label='DXY')
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title('Real-time Technical Chart: Gold vs US Dollar Index', fontsize=14, fontweight='bold', pad=15)
        fig.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()

        photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        files = {'photo': ('chart.png', buf, 'image/png')}
        payload = {'chat_id': MY_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        requests.post(photo_url, data=payload, files=files, timeout=20)
        print("✅ ส่งกราฟเข้ากลุ่มเรียบร้อย!")

    except Exception as e:
        print(f"Report error: {e}")

# ========================================================
# 🌐 2. ฟังก์ชันดึงข่าว (ยิงเข้ากลุ่มทันที ไม่คัดกรองคำ)
# ========================================================
def fetch_and_notify_filtered_news(token):
    global is_first_run
    feeds = {
        "Investing.com": "https://www.investing.com/rss/news_1.rss",
        "CNBC Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    }
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for source, url in feeds.items():
        try:
            response = requests.get(url, headers=headers, timeout=8) # ปรับ Timeout ให้ไวขึ้นเพื่อให้ทันรอบ 10 วินาที
            if response.status_code != 200: continue
            
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            for item in reversed(items):
                title_elem = item.find('title')
                link_elem = item.find('link')
                if title_elem is None or link_elem is None: continue
                
                title = title_elem.text.strip() if title_elem.text else ""
                link = link_elem.text.strip() if link_elem.text else ""
                
                if not link or link in sent_news_links: continue
                sent_news_links.add(link)
                
                # ถ้าบอทจำฐานข้อมูลข่าวเก่าในรอบแรกเสร็จแล้ว ข่าวไหนมาใหม่หลังจากนั้นยิงเข้ากลุ่มทันที!
                if not is_first_run:
                    clean_title = escape_html(title)
                    message = (
                        f"📰 <b>[{source}] อัปเดตข่าวสารตลาดด่วน</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>หัวข้อ:</b> {clean_title}\n\n"
                        f"🔗 <a href='{link}'>คลิกเพื่อเปิดอ่านข่าวตัวเต็ม</a>"
                    )
                    send_telegram_message(token, MY_CHAT_ID, message)
                    time.sleep(0.5)
        except Exception as e:
            print(f"News error from {source}: {e}")
            
    if is_first_run:
        is_first_run = False

# ========================================================
# 🔁 3. ลูปการทำงานหลัก (ปรับเป็นเช็กทุก 10 วินาทีแล้ว)
# ========================================================
def main_bot_process():
    global is_first_run
    token = os.environ.get("TOKEN")
    time.sleep(5) # รอนะบบ Server แป๊บเดียวพอ
    print("🤖 บอทระบบด่วนพิเศษเริ่มทำงานแล้ว...")
    
    # สั่งให้ส่งรายงานกราฟวิเคราะห์รูปแรกทันทีก่อนเลยครับ
    if token:
        try:
            generate_and_send_market_report(token)
        except Exception as e:
            print(f"Initial report error: {e}")
            
    last_report_time = time.time()
    
    while True:
        if not token:
            print("❌ ไม่พบ TOKEN")
            time.sleep(10)
            continue
            
        # ⚡ สั่งรันเช็กข่าวสารใหม่
        try:
            fetch_and_notify_filtered_news(token)
        except Exception as e:
            print(f"News loop error: {e}")
            
        # ส่งกราฟวิเคราะห์ซ้ำตามรอบทุกๆ 1 ชั่วโมง (3600 วินาที)
        current_time = time.time()
        if current_time - last_report_time >= 3600:
            try:
                generate_and_send_market_report(token)
                last_report_time = current_time
            except Exception as e:
                print(f"Report loop error: {e}")
                
        # ⏱️ [แก้ไขตรงนี้]: เปลี่ยนจากนอน 5 นาที เป็นนอนแค่ 10 วินาทีแล้ววนลูปใหม่ทันที!
        time.sleep(10)

threading.Thread(target=main_bot_process, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
