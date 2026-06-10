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

sent_news_links = set()

@app.route('/')
def home():
    return "Forex Core Active Running 🚀"

def escape_html(text):
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try: 
        res = requests.post(url, json=payload, timeout=5)
        # พิมพ์ดูสถานะใน Log ของ Render เผื่อเช็ค Error
        print(f"Telegram Response: {res.status_code}") 
    except Exception as e: 
        print(f"Error sending message: {e}")

# ========================================================
# 📈 1. ลูปส่งกราฟวิเคราะห์ (ทำงานแยกอิสระ ส่งทุกๆ 1 ชั่วโมง)
# ========================================================
def chart_loop_process(token):
    print("📈 เริ่มต้นระบบวิเคราะห์กราฟเทคนิค...")
    while True:
        try:
            print("📈 กำลังประมวลผลกราฟราคาทองคำ & ดอลลาร์...")
            gold_ticker = yf.Ticker("GC=F")       
            oil_ticker = yf.Ticker("CL=F")        
            dxy_ticker = yf.Ticker("DX-Y.NYB")    

            gold_hist = gold_ticker.history(period="7d", interval="1h")
            oil_hist = oil_ticker.history(period="1d")
            dxy_hist = dxy_ticker.history(period="7d", interval="1h")

            if not gold_hist.empty and not dxy_hist.empty and not oil_hist.empty:
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
            print(f"Chart loop error: {e}")
            
        time.sleep(3600) # วาดกราฟใหม่ส่งทุกๆ 1 ชั่วโมง

# ========================================================
# 🌐 2. ลูปเช็กข่าวสารด่วน (ทำงานแยกอิสระ เช็กไวทุกๆ 10 วินาที)
# ========================================================
def news_loop_process(token):
    print("🤖 เริ่มต้นระบบเช็กข่าวสาร Real-time (ทุก 10 วินาที)...")
    
    # รอบแรกสุด บอทจะจำลิงก์ปัจจุบันก่อนเพื่อไม่ให้ข่าวเก่าเด้งถล่มห้อง
    initial_run = True 
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    feeds = {
        "Investing.com": "https://www.investing.com/rss/news_1.rss",
        "CNBC Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    }

    while True:
        for source, url in feeds.items():
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code != 200: continue
                
                root = ET.fromstring(response.content)
                items = root.findall('.//item')
                
                # อ่านจากข่าวเก่าไปข่าวใหม่สุด
                for item in reversed(items):
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    if title_elem is None or link_elem is None: continue
                    
                    title = title_elem.text.strip() if title_elem.text else ""
                    link = link_elem.text.strip() if link_elem.text else ""
                    
                    if not link or link in sent_news_links: continue
                    sent_news_links.add(link)
                    
                    # ถ้าไม่ใช่การรันจำค่าครั้งแรก และมีข่าวใหม่เกิดขึ้น ยิงเข้ากลุ่มทันที!
                    if not initial_run:
                        clean_title = escape_html(title)
                        message = (
                            f"📰 <b>[{source}] อัปเดตข่าวสารตลาดด่วน</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"📌 <b>หัวข้อ:</b> {clean_title}\n\n"
                            f"🔗 <a href='{link}'>คลิกเพื่อเปิดอ่านข่าวตัวเต็ม</a>"
                        )
                        send_telegram_message(token, MY_CHAT_ID, message)
                        time.sleep(0.5) # หน่วงสั้นๆ กันบอทโดน Telegram บล็อก
            except Exception as e:
                print(f"News fetch error from {source}: {e}")
                
        if initial_run:
            print("✅ บอทบันทึกฐานข้อมูลข่าวรอบแรกเสร็จแล้ว กำลังสแตนด์บายรอข่าวใหม่ทุกๆ 10 วินาที...")
            initial_run = False
            
        time.sleep(10) # ⏱️ วนลูปตรวจจับข่าวใหม่ในทุกๆ 10 วินาทีแบบเป๊ะๆ

# ========================================================
# 🔁 3. ฟังก์ชันเตรียมตัวแปร และสั่งรันระบบเบื้องหลัง
# ========================================================
def start_bot():
    token = os.environ.get("TOKEN")
    if not token:
        print("❌ ไม่พบตัวแปร TOKEN ใน Environment Variables ของ Render")
        return
        
    # สั่งแยกรัน 2 ลูปขนานกันไป ไม่ขัดขากันเองแล้วครับ
    threading.Thread(target=chart_loop_process, args=(token,), daemon=True).start()
    threading.Thread(target=news_loop_process, args=(token,), daemon=True).start()

# สั่งให้บอทเริ่มทำงาน
start_bot()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
