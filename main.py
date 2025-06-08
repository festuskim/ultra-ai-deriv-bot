import os
import time
import json
import logging
import websocket
import traceback
from flask import Flask, jsonify
from threading import Thread

# Initialize Flask app first
app = Flask(__name__)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Config values
BASE_STAKE = 2
TRADE_GAP = 5
MAX_PROFIT = 10000
STOP_LOSS_BUFFER = 10

# API Token setup
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN")

# Validate token presence
if not DERIV_API_TOKEN:
    logger.error("❌ DERIV_API_TOKEN not set in environment variables!")
    exit(1)

class AdvancedStrategyManager:
    def adapt_stake(self, profit, current_stake):
        try:
            if profit > 0:
                return current_stake + profit * 0.2
            return max(1.0, current_stake * 0.8)
        except Exception as e:
            logger.error(f"🔴 Stake adaptation error: {str(e)}")
            return BASE_STAKE  # Fallback to base stake

class DerivWebSocketClient:
    def __init__(self, api_token):
        # Validate token format
        if not api_token.startswith("oauth:"):
            logger.error("❌ INVALID TOKEN FORMAT! Must start with 'oauth:'")
            exit(1)
            
        self.api_token = api_token
        self.ws = None
        self.connect()
        
    def connect(self):
        try:
            logger.info("🔌 Connecting to Deriv WebSocket...")
            self.ws = websocket.create_connection(
                "wss://ws.derivws.com/websockets/v3?app_id=1089",
                timeout=10
            )
            logger.info("✅ WebSocket connection established")
            self.authorize()
        except Exception as e:
            logger.error(f"🔥 Connection failed: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            time.sleep(5)
            self.connect()
    
    @property
    def connected(self):
        return self.ws and self.ws.connected
    
    def reconnect(self):
        logger.warning("🔄 Reconnecting to WebSocket...")
        try:
            if self.ws:
                self.ws.close()
        except:
            pass
        time.sleep(2)
        self.connect()
    
    def send(self, data):
        try:
            self.ws.send(json.dumps(data))
            response = self.ws.recv()
            logger.debug(f"📡 Sent: {data} | Received: {response}")
            return response
        except websocket.WebSocketConnectionClosedException:
            logger.warning("🔌 Connection closed during send, reconnecting...")
            self.reconnect()
            return self.send(data)
        except Exception as e:
            logger.error(f"📡 Send error: {str(e)}")
            self.reconnect()
            return self.send(data)

    def authorize(self):
        try:
            logger.info("🔑 Attempting authorization...")
            response = self.send({"authorize": self.api_token})
            auth_data = json.loads(response)
            
            if "error" in auth_data:
                error_msg = auth_data["error"].get("message", "Unknown error")
                logger.error(f"🔒 Authorization FAILED: {error_msg}")
                logger.error("❌ Check your API token and account permissions")
                exit(1)
            
            if "authorize" in auth_data:
                login_id = auth_data["authorize"].get("loginid", "Unknown")
                logger.info(f"✅ Authorization successful for {login_id}")
                return True
            
            logger.error("🚫 Unexpected authorization response")
            logger.debug(f"Response: {auth_data}")
            return False
        except Exception as e:
            logger.error(f"🔥 Authorization failed: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            exit(1)

    def get_balance(self):
        try:
            logger.info("💰 Retrieving account balance...")
            response = self.send({"balance": 1, "subscribe": 0})
            data = json.loads(response)
            
            if "error" in data:
                logger.error(f"🔴 Balance error: {data['error']['message']}")
                return 0.0
                
            if "balance" in data and "balance" in data["balance"]:
                balance = float(data["balance"]["balance"])
                logger.info(f"💵 Current balance: ${balance:.2f}")
                return balance
            
            logger.warning("⚠️ Unexpected balance response")
            logger.debug(f"Response: {data}")
            return 0.0
        except Exception as e:
            logger.error(f"🔥 Balance retrieval failed: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return 0.0
    
    def place_trade(self, amount, contract_type="CALL"):
        try:
            logger.info(f"💱 Placing trade: ${amount:.2f} {contract_type}")
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
                error_msg = buy_response["error"].get("message", "Unknown error")
                logger.error(f"🚨 Trade error: {error_msg}")
                return {"profit": 0}
                
            if "buy" in buy_response:
                contract_id = buy_response["buy"]["contract_id"]
                logger.info(f"📝 Contract ID: {contract_id}")
                start_time = time.time()
                
                while time.time() - start_time < 120:
                    status_resp = self.send({
                        "proposal_open_contract": 1, 
                        "contract_id": contract_id
                    })
                    status = json.loads(status_resp)
                    
                    if "error" in status:
                        error_msg = status["error"].get("message", "Unknown error")
                        logger.error(f"🚨 Contract error: {error_msg}")
                        return {"profit": 0}
                    
                    if status["proposal_open_contract"].get("is_sold", False):
                        payout = float(status["proposal_open_contract"].get("payout", 0))
                        profit = payout - amount
                        logger.info(f"🧾 Trade result: Payout ${payout:.2f} | Profit ${profit:.2f}")
                        return {"profit": profit}
                    
                    logger.info("⏳ Waiting for contract settlement...")
                    time.sleep(1)
            
            logger.warning("⏱️ Trade timed out")
            return {"profit": 0}
        except Exception as e:
            logger.error(f"🔥 Trade execution failed: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            return {"profit": 0}

# Flask route
@app.route("/")
def index():
    return jsonify({
        "status": "operational",
        "bot": "ULTRA AI DERIV BOT",
        "version": "2.0",
        "message": "Trading system is running"
    })

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "timestamp": time.time()})

def run_flask():
    try:
        logger.info("🌐 Starting Flask server...")
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        logger.error(f"🔥 Flask server failed: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")

def start_flask_server():
    try:
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("✅ Flask server started in background thread")
    except Exception as e:
        logger.error(f"🔥 Failed to start Flask thread: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")

def main():
    try:
        logger.info("🔥 Starting Deriv AI Trading Bot")
        
        # Start Flask server
        start_flask_server()
        
        # Initialize trading components
        client = DerivWebSocketClient(DERIV_API_TOKEN)
        strategy = AdvancedStrategyManager()
        
        stake = BASE_STAKE
        total_profit = 0.0
        stop_loss = -STOP_LOSS_BUFFER

        # Main trading loop
        while True:
            try:
                # Check connection status
                if not client.connected:
                    logger.warning("🔌 WebSocket disconnected, reconnecting...")
                    client.connect()
                    time.sleep(2)
                    continue
                
                # Get account balance
                balance = client.get_balance()
                if balance <= 0:
                    logger.error("💀 Zero balance detected! Stopping bot.")
                    break
                
                # Check profit targets
                if total_profit <= stop_loss:
                    logger.warning(f"🛑 Stop loss triggered at ${total_profit:.2f}")
                    break
                    
                if total_profit >= MAX_PROFIT:
                    logger.info(f"🎯 Target reached! ${total_profit:.2f}")
                    break
                
                # Execute trade
                logger.info(f"🔄 Current stake: ${stake:.2f}")
                result = client.place_trade(amount=stake)
                profit = result["profit"]
                total_profit += profit
                
                # Update stake
                stake = strategy.adapt_stake(profit, stake)
                logger.info(f"📊 Total profit: ${total_profit:.2f}")
                
                # Update stop loss
                stop_loss = max(stop_loss, total_profit - STOP_LOSS_BUFFER)
                
                time.sleep(TRADE_GAP)
                
            except websocket.WebSocketConnectionClosedException:
                logger.error("🔌 WebSocket connection closed unexpectedly")
                time.sleep(5)
            except Exception as e:
                logger.error(f"🔴 CRITICAL ERROR IN TRADING LOOP: {str(e)}")
                logger.debug(f"Stack trace: {traceback.format_exc()}")
                time.sleep(10)
                
    except Exception as e:
        logger.error(f"💀 FATAL ERROR IN MAIN: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        exit(1)

if __name__ == "__main__":
    # Add extra space before starting for better log visibility
    logger.info("\n" + "="*50)
    logger.info("🚀 APPLICATION STARTING")
    logger.info("="*50 + "\n")
    
    main()
    
    logger.info("\n" + "="*50)
    logger.info("🛑 APPLICATION STOPPED")
    logger.info("="*50)
