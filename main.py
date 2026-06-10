
                from flask import Flask
import threading
import time
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ========================================================
# ⚙️ [CONFIG: Credentials from your original Replit Bot]
# ========================================================
BOT_TOKEN = "8845436697:AAHurbIeYbHtwBYqjir97M7y_WgSJ8Sh4jY"
CHAT_ID = "-1003911767447"

sent_events = set()

# 🌐 Render Safety Net: Tells Render that your bot is alive and listening
@app.route('/')
def home():
    return "Forex Factory Calendar System - Online & Active 🚀"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=8)
        print(f"🔗 Dispatch Status: {res.status_code}")
    except Exception as e:
        print(f"❌ Telegram Send Error: {e}")

def fetch_and_send_news():
    print("Scanning Forex Factory Calendar...")
    rss_url = "https://www.forexfactory.com/ff_calendar_thisweek.xml"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(rss_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Connection Failed: Status {response.status_code}")
            return
            
        root = ET.fromstring(response.content)
        events = root.findall('.//event')
        
        # Checking the latest 5 events on the feed
        for item in events[:5]:
            title_elem = item.find('title')
            country_elem = item.find('country')
            impact_elem = item.find('impact')
            date_elem = item.find('date')
            time_elem = item.find('time')
            
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else "No Title"
            country = country_elem.text.strip() if country_elem is not None and country_elem.text else "ALL"
            impact = impact_elem.text.strip() if impact_elem is not None and impact_elem.text else "Low"
            ev_date = date_elem.text.strip() if date_elem is not None and date_elem.text else ""
            ev_time = time_elem.text.strip() if time_elem is not None and time_elem.text else ""
            
            # Unique key prevents sending duplicates to your group
            event_key = f"{title}_{country}_{ev_date}_{ev_time}"
            
            if event_key in sent_events:
                continue
                
            sent_events.add(event_key)
            
            # Replit logic: Alert only on High and Medium Impact events
            if impact in ["High", "Medium"]:
                news_message = (
                    f"🔔 *ECONOMIC NEWS ALERT*\n\n"
                    f"📌 *Event:* {title}\n"
                    f"🌍 *Currency:* {country}\n"
                    f"🔥 *Impact:* {impact}\n"
                    f"📅 *Schedule:* {ev_date} {ev_time}"
                )
                send_telegram_message(news_message)
                time.sleep(2)
    except Exception as e:
        print(f"❌ Parsing Failure: {e}")

# 🔁 The continuous loop processor running safely in the background
def news_loop():
    send_telegram_message("🚀 Bot is now running from mobile server!")
    while True:
        fetch_and_send_news()
        time.sleep(600) # Checks for updates every 10 minutes

# ========================================================
# 🚀 System Bootstrapper (Launches background threads)
# ========================================================
def start_bot():
    threading.Thread(target=news_loop, daemon=True).start()

start_bot()

if __name__ == "__main__":
    # Binds port 10000 to keep Render Web Service completely stable
    app.run(host="0.0.0.0", port=10000)
    
