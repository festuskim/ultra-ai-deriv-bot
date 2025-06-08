import os
import time
import json
import logging
import websocket
from flask import Flask
from threading import Thread

# Config values
BASE_STAKE = 2
TRADE_GAP = 5
MAX_PROFIT = 10000
STOP_LOSS_BUFFER = 10  # Allow $10 loss before stopping

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# API Token setup
REQUIRED_PIN = os.getenv("REQUIRED_PIN", "5667")
DERIV_API_TOKEN = os.getenv("***********CtBt")

# Validate token
if not DERIV_API_TOKEN:
    logger.error("❌ DERIV_API_TOKEN not set in environment variables!")
    exit(1)

class AdvancedStrategyManager:
    def adapt_stake(self, profit, current_stake):
        if profit > 0:
            return current_stake + profit * 0.2
        return max(1.0, current_stake * 0.8)

class DerivWebSocketClient:
    def __init__(self, api_token):
        self.api_token = api_token
        self.connect()
        
    def connect(self):
        self.ws = websocket.WebSocket()
        self.ws.connect("wss://ws.derivws.com/websockets/v3?app_id=1089")
        self.authorize()
    
    def reconnect(self):
        logger.warning("🔄 WebSocket disconnected. Reconnecting...")
        time.sleep(2)
        self.connect()
    
    def send(self, data):
        try:
            self.ws.send(json.dumps(data))
            return self.ws.recv()
        except websocket.WebSocketConnectionClosedException:
            self.reconnect()
            return self.send(data)

    def authorize(self):
        response = self.send({"authorize": self.api_token})
        logger.info("🔑 Authorization successful")

    def get_balance(self):
        response = json.loads(self.send({"balance": 1, "subscribe": 0}))
        return float(response["balance"]["balance"])
    
    def place_trade(self, amount, contract_type="CALL"):
        trade_request = {
            "buy": 1,
            "price": str(amount),
            "parameters": {
                "amount": str(amount),
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "m",
                "symbol": "R_50"
            }
        }
        
        response = self.send(trade_request)
        buy_response = json.loads(response)
        
        if "error" in buy_response:
            logger.error(f"🚨 Trade error: {buy_response['error']['message']}")
            return {"profit": 0}
            
        if "buy" in buy_response:
            contract_id = buy_response["buy"]["contract_id"]
            start_time = time.time()
            
            while time.time() - start_time < 120:
                status_resp = self.send({"proposal_open_contract": 1, "contract_id": contract_id})
                status = json.loads(status_resp)
                
                if "error" in status:
                    logger.error(f"🚨 Contract error: {status['error']['message']}")
                    return {"profit": 0}
                
                if status["proposal_open_contract"]["is_sold"]:
                    payout = float(status["proposal_open_contract"]["payout"])
                    profit = payout - amount
                    return {"profit": profit}
                
                time.sleep(1)
        
        logger.warning("⏱️ Trade timed out")
        return {"profit": 0}

@app.route("/")
def index():
    return "🤖 ULTRA AI BOT - OPERATIONAL"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask_server():
    Thread(target=run_flask, daemon=True).start()

def main():
    logger.info("🔥 Starting Deriv AI Trading Bot")
    start_flask_server()

    client = DerivWebSocketClient(DERIV_API_TOKEN)
    strategy = AdvancedStrategyManager()
    
    stake = BASE_STAKE
    total_profit = 0.0
    stop_loss = -STOP_LOSS_BUFFER  # Initial buffer

    while True:
        try:
            balance = client.get_balance()
            logger.info(f"💼 Balance: ${balance:.2f} | 💰 Profit: ${total_profit:.2f}")
            
            if total_profit <= stop_loss:
                logger.warning(f"🛑 Stop loss triggered at ${total_profit:.2f}")
                break
                
            if total_profit >= MAX_PROFIT:
                logger.info(f"🎯 Target reached! ${total_profit:.2f}")
                break
                
            # Execute trade
            result = client.place_trade(amount=stake)
            profit = result["profit"]
            total_profit += profit
            
            # Update stake
            stake = strategy.adapt_stake(profit, stake)
            logger.info(f"🧾 Result: ${profit:.2f} | 🔄 Next Stake: ${stake:.2f}")
            
            # Update stop loss
            stop_loss = max(stop_loss, total_profit - STOP_LOSS_BUFFER)
            
            time.sleep(TRADE_GAP)
            
        except Exception as e:
            logger.error(f"🔴 CRITICAL ERROR: {str(e)}")
            time.sleep(10)

if __name__ == "__main__":
    main()
