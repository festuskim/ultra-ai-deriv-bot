import websocket
import json
import logging
import time

logger = logging.getLogger(__name__)

class DerivWSClient:
    def __init__(self, api_token):
        self.api_token = api_token
        self.ws = None

    def connect(self):
        self.ws = websocket.WebSocket()
        self.ws.connect("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        self.authorize()

    def authorize(self):
        self.ws.send(json.dumps({"authorize": self.api_token}))
        response = self._receive()
        if response.get("msg_type") != "authorize":
            raise Exception("Authorization failed")
        logger.info("✅ Authorized with Deriv")

    def get_balance(self):
        self.ws.send(json.dumps({"balance": 1, "subscribe": 0}))
        response = self._receive()
        return float(response["balance"]["balance"])

    def trade(self, stake, symbol="R_50", duration=1, contract_type="CALL"):
        proposal = {
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": duration,
            "duration_unit": "m",
            "symbol": symbol
        }
        self.ws.send(json.dumps(proposal))
        proposal_response = self._receive()
        if "error" in proposal_response:
            logger.error("❌ Proposal error: %s", proposal_response["error"]["message"])
            return
        buy_payload = {
            "buy": proposal_response["proposal"]["id"],
            "price": stake
        }
        self.ws.send(json.dumps(buy_payload))
        buy_response = self._receive()
        if "error" in buy_response:
            logger.error("❌ Buy error: %s", buy_response["error"]["message"])
            return
        logger.info(f"✅ Trade executed: {buy_response}")

    def _receive(self):
        while True:
            result = json.loads(self.ws.recv())
            if "error" in result:
                logger.error("❌ WebSocket error: %s", result["error"]["message"])
                break
            return result