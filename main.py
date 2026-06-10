from flask import Flask
import threading
import time
import os
import io
import requests
import xml.etree.ElementTree as ET
import yfinance as yf

# ตั้งค่าไม่ให้ matplotlib เปิดหน้าต่าง GUI เพื่อให้รันบนเซิร์ฟเวอร์ได้ราบรื่น
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# ========================================================
# ⚙️ [ตั้งค่าเลข ID ห้องของพี่ตรงนี้เรียบร้อยครับ!]
# ========================================================
MY_CHAT_ID = -1003911767447  # เลขกลุ่มของพี่ใส่ตรงนี้เรียบร้อยครับ

# ตัวแปรจำสถานะเพื่อป้องกันส่งซ้ำ
LAST_NEWS_LINK = None
sent_news_links = set()
is_first_run = True

@app.route('/')
def home():
    return "Forex Advanced System Running 🚀"

def escape_html(text):
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ฟังก์ชันส่งข้อความธรรมดา
def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    try: 
        requests.post(url, json=payload, timeout=10)
    except Exception as e: 
        print(f"เกิดข้อผิดพลาดในการส่งข้อความ: {e}")

# ========================================================
# 📈 1. ฟังก์ชันดึงราคา, วิเคราะห์เทคนิค และวาดกราฟ (ยิงเข้ากลุ่ม)
# ========================================================
def generate_and_send_market_report(token):
    print("📈 ระบบกำลังคำนวณราคา Real-time & วาดกราฟเทคนิค...")
    try:
        # ดึงข้อมูลจากตลาดการเงินโลก (ทองคำ, น้ำมัน WTI, ดัชนีดอลลาร์ DXY)
        gold_ticker = yf.Ticker("GC=F")       
        oil_ticker = yf.Ticker("CL=F")        
        dxy_ticker = yf.Ticker("DX-Y.NYB")    

        gold_hist = gold_ticker.history(period="7d", interval="1h")
        oil_hist = oil_ticker.history(period="1d")
        dxy_hist = dxy_ticker.history(period="7d", interval="1h")

        if gold_hist.empty or dxy_hist.empty or oil_hist.empty:
            print("ไม่สามารถดึงข้อมูลราคาจาก yfinance ได้ในขณะนี้")
            return

        current_gold = gold_hist['Close'].iloc[-1]
        current_oil = oil_hist['Close'].iloc[-1]
        current_dxy = dxy_hist['Close'].iloc[-1]

        # คำนวณเส้นเทรนด์ Moving Average 20 เพื่อหาสัญญาณ ซื้อ/ขาย อัตโนมัติ
        gold_hist['MA20'] = gold_hist['Close'].rolling(window=20).mean()
        ma20_val = gold_hist['MA20'].iloc[-1]

        if current_gold > ma20_val:
            recommendation = "📈 <b>วิเคราะห์เทคนิค (1H):</b> เทรนด์ขาขึ้น (BULLISH)\n🎯 <b>คำแนะนำการเทรด:</b> หาจังหวะเข้าฝั่ง <b>BUY / LONG</b> ได้เปรียบกว่าครับ"
        else:
            recommendation = "📉 <b>วิเคราะห์เทคนิค (1H):</b> เทรนด์ขาลง (BEARISH)\n🎯 <b>คำแนะนำการเทรด:</b> หาจังหวะเข้าฝั่ง <b>SELL / SHORT</b> ได้เปรียบกว่าครับ"

        # ข้อความวิเคราะห์สรุปใต้รูปกราฟ
        caption = (
            f"📊 <b>รายงานดัชนีตลาด Real-Time & บทวิเคราะห์</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🪙 <b>ราคาทองคำ (XAU/USD):</b> ${current_gold:,.2f}\n"
            f"🛢️ <b>น้ำมันดิบ WTI:</b> ${current_oil:,.2f} / บาร์เรล\n"
            f"💵 <b>ดัชนีดอลลาร์ (DXY):</b> {current_dxy:,.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{recommendation}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <i>วิเคราะห์อัตโนมัติเบื้องต้น โปรดบริหารความเสี่ยงเสมอก่อนออกออเดอร์</i>"
        )

        # เริ่มกระบวนการสร้างและวาดรูปกราฟเปรียบเทียบ ทองคำ VS ดอลลาร์
        fig, ax1 = plt.subplots(figsize=(10, 5))
        
        # แกนซ้าย: ราคาทอง (เส้นสีทอง)
        color = '#d4af37'
        ax1.set_xlabel('Date & Time (Past 7 Days)', fontweight='bold')
        ax1.set_ylabel('Gold Price ($/oz)', color=color, fontweight='bold')
        ax1.plot(gold_hist.index, gold_hist['Close'], color=color, linewidth=2, label='Gold (XAU/USD)')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle=':', alpha=0.5)

        # แกนขวา: ดัชนีดอลลาร์ (เส้นประสีน้ำเงิน)
        ax2 = ax1.twinx()
        color = '#1f77b4'
        ax2.set_ylabel('US Dollar Index (DXY)', color=color, fontweight='bold')
        ax2.plot(dxy_hist.index, dxy_hist['Close'], color=color, linewidth=1.5, linestyle='--', label='DXY')
        ax2.tick_params(axis='y', labelcolor=color)

        plt.title('Real-time Technical Chart: Gold vs US Dollar Index', fontsize=14, fontweight='bold', pad=15)
        fig.tight_layout()

        # แปลงรูปภาพลง Memory Buffer เพื่อเตรียมส่งผ่าน API
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close()

        # ส่งภาพกราฟพร้อมบทวิเคราะห์เข้ากลุ่มพี่ตรงๆ
        photo_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        files = {'photo': ('chart.png', buf, 'image/png')}
        payload = {'chat_id': MY_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        requests.post(photo_url, data=payload, files=files, timeout=20)
        print("✅ ส่งกราฟวิเคราะห์ทางเทคนิคเข้ากลุ่มเรียบร้อยแล้ว!")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการสร้างรายงานกราฟ: {e}")

# ========================================================
# 🌐 2. ฟังก์ชันดึงข่าว (คัดกรองเฉพาะข่าวสงคราม ดอกเบี้ย และตัวเลขเศรษฐกิจแรงๆ)
# ========================================================
def fetch_and_notify_filtered_news(token):
    global is_first_run
    feeds = {
        "Investing.com": "https://www.investing.com/rss/news_1.rss",
        "CNBC Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    }
    
    # คำค้นหาสำหรับคัดกรองเฉพาะข่าวใหญ่ที่มีผลรุนแรงต่อ Forex/ทองคำ
    target_keywords = ['war', 'military', 'attack', 'strike', 'unemployment', 'payroll', 'jobless', 'oil', 'crude', 'gold', 'xau', 'fed', 'inflation', 'rate']
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for source, url in feeds.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200: continue
            
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            # ตรวจสอบข่าวจากเก่าไปใหม่
            for item in reversed(items):
                title_elem = item.find('title')
                link_elem = item.find('link')
                if title_elem is None or link_elem is None: continue
                
                title = title_elem.text.strip() if title_elem.text else ""
                link = link_elem.text.strip() if link_elem.text else ""
                
                if not link or link in sent_news_links: continue
                sent_news_links.add(link)
                
                # เช็คว่าหัวข้อข่าวมีคำสำคัญที่เราคัดกรองไว้ไหม
                has_keyword = any(kw in title.lower() for kw in target_keywords)
                
                # ดึงข่าวใหม่เฉพาะหลังจากบอทรันแล้ว และมีคีย์เวิร์ดตรงตามที่กำหนด
                if not is_first_run and has_keyword:
                    clean_title = escape_html(title)
                    message = (
                        f"🚨 <b>[{source}] Breaking Financial Focus!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>หัวข้อข่าวสำคัญ:</b> {clean_title}\n\n"
                        f"🔗 <a href='{link}'>คลิกเพื่อเปิดอ่านข่าวตัวเต็ม</a>"
                    )
                    send_telegram_message(token, MY_CHAT_ID, message)
                    time.sleep(1)
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการดึงข่าวสารจาก {source}: {e}")
            
    if is_first_run:
        is_first_run = False

# ========================================================
# 🔁 3. ระบบลูปทำงานเบื้องหลัง (Background Loops)
# ========================================================
def main_bot_process():
    token = os.environ.get("TOKEN")
    time.sleep(10) # รอนะบบ Server สตาร์ทตัว
    print("🤖 บอทขั้นสูงเริ่มทำงานระบบตรวจสอบตลาดแล้ว...")
    
    # ตัวนับเวลาสำหรับส่งกราฟทุกๆ 1 ชั่วโมง
    last_report_time = 0
    
    while True:
        if not token:
            print("❌ ไม่พบตัวแปร TOKEN ในระบบ Render ของพี่ครับ")
            time.sleep(60)
            continue
            
        # 1. เช็คข่าวสารด่วน (คัดกรองคีย์เวิร์ดแรงๆ) ทุก 5 นาที
        try:
            fetch_and_notify_filtered_news(token)
        except Exception as e:
            print(f"News loop error: {e}")
            
        # 2. ตรวจสอบส่งรายงานวิเคราะห์เทคนิคและรูปกราฟทุกๆ 1 ชั่วโมง (3600 วินาที)
        current_time = time.time()
        if current_time - last_report_time >= 3600:
            try:
                generate_and_send_market_report(token)
                last_report_time = current_time
            except Exception as e:
                print(f"Report loop error: {e}")
                
        time.sleep(300) # แอบไปสแกนรอบใหม่ทุก 5 นาที เพื่อไม่ให้หนักระบบ

# สั่งให้ลูปทำงานด้านหลังแบบขนานคู่ไปกับเซิร์ฟเวอร์
threading.Thread(target=main_bot_process, daemon=True).start()

if __name__ == "__main__":
    # รันพอร์ต 10000 ตามมาตรฐานเว็บ Render แบบที่พี่ใช้ในโค้ดเก่าเลยครับ
    app.run(host="0.0.0.0", port=10000)
