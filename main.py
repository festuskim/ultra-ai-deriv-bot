import os
import time
import logging
from flask import Flask
from threading import Thread
from deriv_ws_client import DerivWebSocketClient
from ai_strategy_manager import AdvancedStrategyManager
from config import BASE_STAKE, TRADE_GAP, TARGET_PROFIT, MAX_PROFIT, STOP_LOSS

# Flask app for Railway keep-alive
app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# API Token and PIN from env
REQUIRED_PIN = os.getenv("REQUIRED_PIN", "5667")
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "YOUR_API_TOKEN")

@app.route("/")
def index():
    return f"🤖 ULTRA AI BOT LIVE | PIN: {REQUIRED_PIN} | API: {'SET' if DERIV_API_TOKEN != 'YOUR_API_TOKEN' else 'NOT SET'}"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask_server():
    Thread(target=run_flask).start()

def main():
    logger.info("🔥 Live Deriv AI Trading Bot Started")
    start_flask_server()

    client = DerivWebSocketClient(DERIV_API_TOKEN)
    strategy = AdvancedStrategyManager()
    stake = BASE_STAKE
    total_profit = 0.0

    while True:
        balance = client.get_balance()
        logger.info(f"💼 Account Balance: ${balance:.2f}")

        if balance <= STOP_LOSS:
            logger.warning("🛑 Stop Loss Hit. Halting Trading.")
            break

        if total_profit >= MAX_PROFIT:
            logger.info("🎯 Target Reached! Stopping bot at $10,000 profit.")
            break

        result = client.place_trade(amount=stake, contract_type="CALL")
        profit = result.get("profit", 0)
        total_profit += profit

        logger.info(f"🧾 Trade Result: ${profit:.2f} | Total Profit: ${total_profit:.2f}")

        stake = strategy.adapt_stake(profit, stake)
        time.sleep(TRADE_GAP)

if __name__ == "__main__":
    main()