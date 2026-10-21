from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os
import requests

app = Flask(__name__)
CORS(app)

# ============ 텔레그램 설정 ============
# Render 환경변수 TELEGRAM_BOT_TOKEN 에 넣으면 자동 사용
# 없으면 빈 값 -> 텔레그램 전송 스킵 (서버는 정상 작동)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")  
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "-1004340608403")
# =====================================

latest_signal = {"signal": "WAIT", "price": 0, "time": 0, "profit": 0, "account": "", "raw": {}}
history = []

def send_telegram(text):
    """텔레그램 채널로 최종이용자 폼 전송"""
    if not BOT_TOKEN:
        print(f"[TELEGRAM] 토큰 없음 - 전송 스킵: {text[:50]}")
        return False
    try:
        base = f"https://api.telegram.org/bot{BOT_TOKEN}"
        # 최종이용자 폼 꾸미기
        r = requests.post(f"{base}/sendMessage", json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=8)
        print(f"[TELEGRAM] 전송 결과: {r.status_code} {r.text[:200]}")
        return r.json().get("ok", False)
    except Exception as e:
        print(f"[TELEGRAM] 오류: {e}")
        return False

def format_final_user_message(data):
    """최종이용자가 보는 텔레그램 폼 생성"""
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
    else:  # WAIT
        return f"""🟦 <b>MNQ V21 대기중</b>
신호: WAIT
가격: {price}
수익: {profit}
계좌: {account}
시간: {t}

<code>{{"signal":"WAIT","price":{price}}}</code>"""

@app.route("/")
def root():
    return jsonify({
        "서비스": "mnq-v21-server", 
        "상태": "정상", 
        "버전": "V21-Telegram",
        "telegram": "연결됨" if BOT_TOKEN else "토큰 없음 - 환경변수 TELEGRAM_BOT_TOKEN 필요",
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
    
    # >>> 텔레그램 최종이용자 폼 전송 <<<
    tg_text = format_final_user_message(latest_signal)
    tg_ok = send_telegram(tg_text)
    
    return jsonify({"ok": True, "received": latest_signal, "telegram_sent": tg_ok})

@app.route("/api/history")
def api_history():
    return jsonify(history[-20:])

@app.route("/api/test-telegram")
def test_telegram():
    """브라우저에서 https://.../api/test-telegram 접속하면 테스트 메시지 발송"""
    msg = f"✅ MNQ V21 테스트 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n서버: mnq-v21-server-jxdu\n상태: 정상"
    ok = send_telegram(msg)
    return jsonify({"ok": ok, "bot_token_set": bool(BOT_TOKEN), "channel": CHANNEL_ID, "message": msg})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
