"""
MNQ v21 Server - Render용
GitHub 저장소: kim1303/mnq-v21-server
Render 주소: https://mnq-v21-server.onrender.com

Admin_PC_Complete.html이 부르는 엔드포인트와 일치시킴:
- POST /api/signal          : 관리자 매수/매도/청산/긴급정지 신호
- POST /api/npoint-sync     : nPoint 승인/차단 목록 저장 (Render 경유)
- GET  /api/kiwoom/status   : 키움 브릿지 상태
- GET  /api/kiwoom/executions : 키움 체결 목록
- GET  /api/profit          : 수익 (Admin / Mini App 공용)
- GET  /api/signal          : 최근 신호 목록 확인용
- GET  /                   : 살아있는지 확인용

실행 (로컬):
  pip install -r requirements.txt
  python server_websocket.py
  -> http://localhost:5000/

실행 (Render):
  Start Command: gunicorn server_websocket:app --bind 0.0.0.0:$PORT
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Admin PC / 텔레그램 폼이 다른 주소에서 불러도 되게 함

# ---- 메모리 저장 (Render 무료는 재시작하면 초기화됨, 영구 저장은 nPoint가 맡음) ----
SIGNALS = []          # 최근 신호 100개
NPOINT_CACHE = {      # 마지막으로 받은 nPoint 동기화 내용
    "approved_users": [],
    "blocked_users": [],
    "updated_at": None,
}
PROFIT_CACHE = {
    "total": 1284.0,
    "today": -210.0,
    "updated_at": None,
}

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "service": "mnq-v21-server",
        "time": now_str(),
        "signals": len(SIGNALS),
        "npoint_updated_at": NPOINT_CACHE.get("updated_at"),
    })

@app.route("/api/profit", methods=["GET"])
def get_profit():
    return jsonify({
        "ok": True,
        "total": PROFIT_CACHE["total"],
        "today": PROFIT_CACHE["today"],
        "profit": PROFIT_CACHE["total"],
        "updated_at": PROFIT_CACHE.get("updated_at") or now_str(),
    })

@app.route("/api/profit", methods=["POST"])
def set_profit():
    data = request.get_json(silent=True) or {}
    if "total" in data:
        try:
            PROFIT_CACHE["total"] = float(data["total"])
        except Exception:
            pass
    if "today" in data:
        try:
            PROFIT_CACHE["today"] = float(data["today"])
        except Exception:
            pass
    PROFIT_CACHE["updated_at"] = now_str()
    return jsonify({"ok": True, "profit": PROFIT_CACHE})

@app.route("/api/signal", methods=["POST"])
def post_signal():
    data = request.get_json(silent=True) or {}
    sig = {
        "type": data.get("type", data.get("action", "SIGNAL")),
        "action": data.get("action", data.get("type", "SIGNAL")),
        "symbol": data.get("symbol", "MNQ"),
        "user": data.get("user", data.get("name", "")),
        "text": data.get("text", ""),
        "time": now_str(),
        "raw": data,
    }
    SIGNALS.append(sig)
    if len(SIGNALS) > 100:
        del SIGNALS[:-100]
    # Render 로그에도 남김 (Render Logs에서 확인 가능)
    print(f"[SIGNAL] {sig['time']} {sig['action']} {sig['symbol']} {sig['user']}", flush=True)
    return jsonify({"ok": True, "saved": sig, "count": len(SIGNALS)})

@app.route("/api/signal", methods=["GET"])
def get_signal():
    return jsonify({"ok": True, "signals": list(reversed(SIGNALS[-20:])), "count": len(SIGNALS)})

@app.route("/api/npoint-sync", methods=["POST"])
def npoint_sync():
    data = request.get_json(silent=True) or {}
    # Admin PC가 보내는 형태: {approved_users, blocked_users, ...} 또는 {payload: {...}}
    payload = data.get("payload", data)
    if isinstance(payload, dict):
        if "approved_users" in payload:
            NPOINT_CACHE["approved_users"] = payload["approved_users"]
        if "blocked_users" in payload:
            NPOINT_CACHE["blocked_users"] = payload["blocked_users"]
        NPOINT_CACHE["updated_at"] = now_str()
        NPOINT_CACHE["last_payload"] = payload
    print(f"[NPOINT-SYNC] {now_str()} approved={len(NPOINT_CACHE['approved_users'])} blocked={len(NPOINT_CACHE['blocked_users'])}", flush=True)
    return jsonify({"ok": True, "cached": NPOINT_CACHE})

@app.route("/api/npoint-sync", methods=["GET"])
def npoint_get():
    return jsonify({"ok": True, "cached": NPOINT_CACHE})

@app.route("/api/kiwoom/status", methods=["GET"])
def kiwoom_status():
    # 키움 브릿지는 로컬 PC(127.0.0.1:5000)에 있음. Render에서는 직접 연결이 안 되므로 대기중으로 알림.
    # 로컬 브릿지가 살아있으면 Admin PC가 로컬 주소를 먼저 쓰고, 실패하면 여기로 옴.
    return jsonify({
        "ok": True,
        "connected": False,
        "status": "waiting",
        "message": "Kiwoom bridge is local (127.0.0.1:5000). Render reports waiting.",
        "time": now_str(),
    })

@app.route("/api/kiwoom/executions", methods=["GET"])
def kiwoom_executions():
    return jsonify({"ok": True, "executions": [], "time": now_str()})

@app.route("/api/users", methods=["GET"])
def get_users():
    return jsonify({
        "ok": True,
        "approved_users": NPOINT_CACHE.get("approved_users", []),
        "blocked_users": NPOINT_CACHE.get("blocked_users", []),
        "updated_at": NPOINT_CACHE.get("updated_at"),
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Render는 PORT 환경변수를 줌. 로컬은 5000.
    app.run(host="0.0.0.0", port=port, debug=False)
