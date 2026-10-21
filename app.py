from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os
import requests

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")  
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "-1003987555752")

latest_signal = {"signal": "WAIT", "price": 0, "time": 0, "profit": 0, "account": "", "raw": {}}
history = []

def send_telegram_debug(text):
    """텔레그램 전송 - 전체 응답 반환"""
    if not BOT_TOKEN:
        return {"ok": False, "error": "NO_TOKEN", "detail": "TELEGRAM_BOT_TOKEN 환경변수 없음"}
    try:
        base = f"https://api.telegram.org/bot{BOT_TOKEN}"
        r = requests.post(f"{base}/sendMessage", json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=8)
        try:
            resp_json = r.json()
        except:
            resp_json = {"raw_text": r.text[:500], "status_code": r.status_code}
        
        print(f"[TELEGRAM] {r.status_code} {resp_json}")
        return resp_json
    except Exception as e:
        print(f"[TELEGRAM] 예외: {e}")
        return {"ok": False, "error": "EXCEPTION", "detail": str(e)}

def format_final_user_message(data):
    signal = data.get("signal", "WAIT")
    price = data.get("price", 0)
    profit = data.get("profit", 0)
    account = data.get("account", "-")
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    
    if signal == "BUY":
        return f"""🟢 <b>MNQ V21 매수 신호</b>
<b>신호: BUY</b>
가격: {price}
수익: {profit}
계좌: {account}
시간: {t}

<code>BUY | {price} | {profit}</code>"""
    elif signal == "SELL":
        return f"""🔴 <b>MNQ V21 매도 신호</b>
<b>신호: SELL</b>
가격: {price}
수익: {profit}
계좌: {account}
시간: {t}

<code>SELL | {price} | {profit}</code>"""
    elif signal == "CLOSE" or "청산" in signal:
        return f"""💰 <b>포지션 청산</b>
수익 확정: {profit}
최종 가격: {price}
계좌 잔고: {account}
시간: {t}"""
    else:
        return f"""🟦 <b>MNQ V21 대기중</b>
신호: WAIT
가격: {price}
수익: {profit}
계좌: {account}
시간: {t}"""

@app.route("/")
def root():
    return jsonify({
        "서비스": "mnq-v21-server", 
        "상태": "정상", 
        "버전": "V21-DEBUG",
        "telegram_token_set": bool(BOT_TOKEN),
        "token_preview": BOT_TOKEN[:10] + "..." + BOT_TOKEN[-5:] if BOT_TOKEN and len(BOT_TOKEN) > 15 else "없음",
        "channel": CHANNEL_ID,
        "routes": ["/", "/health", "/api", "/api/history", "/api/test-telegram"]
    })

@app.route("/health")
def health():
    return jsonify({"ok": True, "latest": latest_signal, "uptime": time.time(), "telegram": bool(BOT_TOKEN)})

@app.route("/api", methods=["GET","POST"])
@app.route("/api/", methods=["GET","POST"])
def api():
    global latest_signal
    if request.method == "GET":
        return jsonify(latest_signal)
    
    data = request.get_json(force=True, silent=True) or {}
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
    
    tg_text = format_final_user_message(latest_signal)
    tg_resp = send_telegram_debug(tg_text)
    
    return jsonify({"ok": True, "received": latest_signal, "telegram_response": tg_resp})

@app.route("/api/history")
def api_history():
    return jsonify(history[-20:])

@app.route("/api/test-telegram")
def test_telegram():
    msg = f"✅ MNQ V21 테스트 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n서버: mnq-v21-server-jxdu\n상태: 정상\n최종이용자 폼 테스트"
    resp = send_telegram_debug(msg)
    return jsonify({
        "ok": resp.get("ok", False),
        "bot_token_set": bool(BOT_TOKEN),
        "token_preview": BOT_TOKEN[:10] + "..." if BOT_TOKEN else "없음",
        "channel": CHANNEL_ID,
        "message": msg,
        "telegram_full_response": resp,
        "hint": "telegram_full_response에서 error_code와 description을 확인하세요. 'Unauthorized'면 토큰 폐기, 'chat not found'면 채널ID 또는 봇 관리자 권한 문제"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
