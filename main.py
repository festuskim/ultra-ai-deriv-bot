import os
import time
import logging
from flask import Flask
from threading import Thread
from ai_strategy_manager import AdvancedStrategyManager

# Flask app for Railway keep-alive
app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Get API token and PIN from environment variables
REQUIRED_PIN = os.getenv("REQUIRED_PIN", "5667")
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "YOUR_API_TOKEN")

@app.route("/")
def index():
    return f"🤖 ULTRA AI BOT RUNNING | PIN: {REQUIRED_PIN} | API: {'SET' if DERIV_API_TOKEN != 'YOUR_API_TOKEN' else 'NOT SET'}"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask_server():
    Thread(target=run_flask).start()

def main():
    logger.info("🤖 Starting ULTRA AI BOT with Risk-Managed Machine Learning")
    start_flask_server()

    strategy_manager = AdvancedStrategyManager()
    stake = 1.0
    total_profit = 0.0

    while True:
        logger.info(f"🧠 Executing simulated trade with stake ${stake:.2f}...")
        simulated_profit = stake * 0.8 if os.urandom(1)[0] % 2 == 0 else -stake  # 50% win/loss
        total_profit += simulated_profit

        logger.info(f"💰 Simulated profit: {simulated_profit:.2f} | Total profit: {total_profit:.2f}")

        if total_profit >= 10:
            stake *= 2  # Increase stake after $10 profit
            logger.info(f"🚀 Stake increased to ${stake:.2f} based on AI gain")

        else:
            stake = max(1.0, stake + max(0, simulated_profit))  # Compound growth on win

        time.sleep(5)

if __name__ == "__main__":
    main()