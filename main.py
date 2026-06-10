from flask import Flask
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Forex Bot Running 🚀"

def bot():
    while True:
        print("Bot running...")
        time.sleep(60)

threading.Thread(target=bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
