from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os

app = Flask(__name__)
CORS(app)

# 메모리 저장 (Render Free는 휘발성 - 실제 운영은 파일/DB 권장)
latest_signal = {"signal": "WAIT", "price": 0, "time": 0, "profit": 0, "account": ""}
history = []

@app.route("/")
def root():
    return jsonify({"status":"ok", "service":"mnq-v21-server", "version":"V21"})

@app.route("/health")
def health():
    return jsonify({"ok": True, "latest": latest_signal, "uptime": time.time()})

@app.route("/api", methods=["GET","POST"])
def api():
    global latest_signal
    if request.method == "GET":
        return jsonify(latest_signal)
    
    data = request.get_json(force=True, silent=True) or {}
    # 관리자 폼에서 오는 신호
    signal = data.get("signal") or data.get("action") or "WAIT"
    signal = str(signal).upper()
    
    latest_signal = {
        "signal": signal,
        "price": data.get("price", 0),
        "time": int(time.time()),
        "profit": data.get("profit", 0),
        "account": data.get("account", ""),
        "raw": data
    }
    history.append(latest_signal)
    if len(history) > 100:
        history.pop(0)
    
    print(f"[SERVER] 수신: {latest_signal}")
    return jsonify({"ok": True, "received": latest_signal, "return": 0})

@app.route("/api/history")
def api_history():
    return jsonify(history[-20:])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
