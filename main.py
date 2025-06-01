import os
import time
import logging
from flask import Flask
from threading import Thread
from deriv_ws_client import DerivWebSocketClient
from ai_strategy_manager import AdvancedStrategyManager

# Config values - adjust these or import from config.py if you want
BASE_STAKE = 2          # Starting stake amount in USD
TRADE_GAP = 5           # Seconds between trades
MAX_PROFIT = 10000      # Target profit to stop the bot

# Flask app for Railway keep-alive
app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# API Token from environment variables
REQUIRED_PIN = os.getenv("REQUIRED_PIN", "5667")
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "YOUR_API_TOKEN")

@app.route("/")
def index():
    return f"🤖 ULTRA AI BOT LIVE | PIN: {REQUIRED_PIN} | API: {'SET' if DERIV_API_TOKEN != 'YOUR_API_TOKEN' else 'NOT SET'}"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask_server():
    Thread(target=run_flask).start()

def get_dynamic_stop_loss(profit):
    """
    Returns dynamic stop loss based on current total profit:
    If profit is 10 -> SL = 5
    If profit is 20 -> SL = 15
    If profit is 30 -> SL = 25
    and so on...
    """
    base = int(profit // 10) * 10
    return max(0, base - 5)

def main():
    logger.info("🔥 Live Deriv AI Trading Bot Started")
    start_flask_server()

    client = DerivWebSocketClient(DERIV_API_TOKEN)
    strategy = AdvancedStrategyManager()
    stake = BASE_STAKE
    total_profit = 0.0
    stop_loss = get_dynamic_stop_loss(total_profit)

    while True:
        balance = client.get_balance()
        logger.info(f"💼 Account Balance: ${balance:.2f}")

        if total_profit <= stop_loss:
            logger.warning(f"🛑 Dynamic Stop Loss Hit (${stop_loss:.2f}). Halting Trading.")
            break

        if total_profit >= MAX_PROFIT:
            logger.info("🎯 Target Reached! Stopping bot at $10,000 profit.")
            break

        result = client.place_trade(amount=stake, contract_type="CALL")
        profit = result.get("profit", 0)
        total_profit += profit

        logger.info(f"🧾 Trade Result: ${profit:.2f} | Total Profit: ${total_profit:.2f}")

        stake = strategy.adapt_stake(profit, stake)
        stop_loss = get_dynamic_stop_loss(total_profit)

        time.sleep(TRADE_GAP)

if __name__ == "__main__":
    main()
