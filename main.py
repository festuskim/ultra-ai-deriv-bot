import os
import time
import logging
from flask import Flask
from threading import Thread
from ai_strategy_manager import AdvancedStrategyManager
from deriv_ws_client import DerivWSClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app to keep the Railway app alive
app = Flask(__name__)

REQUIRED_PIN = os.getenv("REQUIRED_PIN", "5667")
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "YOUR_API_TOKEN")
TARGET_PROFIT = 10000.0
STARTING_BALANCE = 2.0

@app.route("/")
def index():
    return f"🤖 LIVE Deriv Bot Running | PIN: {REQUIRED_PIN} | API: {'SET' if DERIV_API_TOKEN != 'YOUR_API_TOKEN' else 'NOT SET'}"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask_server():
    Thread(target=run_flask).start()

def main():
    logger.info("🚀 Starting Deriv Bot with Real Trades and Risk Management")
    start_flask_server()

    strategy_manager = AdvancedStrategyManager()
    deriv_client = DerivWSClient(DERIV_API_TOKEN)
    deriv_client.connect()

    balance = deriv_client.get_balance()
    logger.info(f"💰 Current balance: ${balance:.2f}")

    if balance < STARTING_BALANCE:
        logger.error("❌ Not enough balance to begin trading")
        return

    starting_balance = balance
    stake = STARTING_BALANCE
    active = True

    while active:
        balance = deriv_client.get_balance()
        profit = balance - starting_balance
        logger.info(f"📊 Profit so far: ${profit:.2f}")

        if profit >= TARGET_PROFIT:
            logger.info(f"🎯 Target profit of ${TARGET_PROFIT} reached! Stopping bot.")
            active = False
            break

        if balance <= 0.35:
            logger.warning("⚠️ Balance too low to continue trading. Stopping bot.")
            active = False
            break

        logger.info("📈 Executing real trade...")
        deriv_client.trade(stake=stake, symbol="R_50", duration=1, contract_type="CALL")
        time.sleep(65)

if __name__ == "__main__":
    main()