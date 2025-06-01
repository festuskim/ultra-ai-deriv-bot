import websocket
import json
import time

class DerivWebSocketClient:
    def __init__(self, api_token):
        self.api_token = api_token
        self.ws = websocket.WebSocket()
        self.ws.connect("wss://ws.derivws.com/websockets/v3?app_id=1089")
        self.authorize()

    def authorize(self):
        auth_data = json.dumps({"authorize": self.api_token})
        self.ws.send(auth_data)
        self.ws.recv()

    def get_balance(self):
        self.ws.send(json.dumps({"balance": 1, "subscribe": 0}))
        response = json.loads(self.ws.recv())
        return float(response["balance"]["balance"])

    def place_trade(self, amount, contract_type="CALL"):
        duration = 1
        self.ws.send(json.dumps({
            "buy": 1,
            "price": str(amount),
            "parameters": {
                "amount": str(amount),
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": "R_50"
            }
        }))
        buy_response = json.loads(self.ws.recv())
        if "buy" in buy_response:
            contract_id = buy_response["buy"]["contract_id"]
            while True:
                self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id}))
                status = json.loads(self.ws.recv())
                if status["proposal_open_contract"]["is_sold"]:
                    payout = status["proposal_open_contract"]["payout"]
                    profit = payout - amount
                    return {"profit": profit}
                time.sleep(1)
        return {"profit": 0}