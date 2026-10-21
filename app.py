from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import os
import requests

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")  
CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "-1003987555752")
FINAL_FORM_URL = os.environ.get("FINAL_FORM_URL", "https://shiny-hall-b9ed.duribun8.workers.dev")

latest_signal = {"signal": "WAIT", "price": 0, "time": 0, "profit": 0, "account": "", "raw": {}}
history = []

def tg_api(method, payload):
    if not BOT_TOKEN:
        return {"ok": False, "error": "NO_TOKEN"}
    base = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        r = requests.post(base, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_telegram_debug(text, with_button=False, chat_id=None):
    """텔레그램 전송 - 채널 또는 개인 채팅"""
    target = chat_id or CHANNEL_ID
    payload = {
        "chat_id": target,
        "text": text,
        "parse_mode": "HTML"
    }
    if with_button:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "📱 최종이용자 폼 열기", "url": FINAL_FORM_URL}]
            ]
        }
    return tg_api("sendMessage", payload)

def send_with_fixed_keyboard(chat_id, text):
    """그림처럼 하단 고정 '매매 확인' 버튼 생성"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "keyboard": [
                [{"text": "매매 확인"}]
            ],
            "resize_keyboard": True,
            "is_persistent": True,
            "one_time_keyboard": False
        }
    }
    return tg_api("sendMessage", payload)

def send_form_with_both(chat_id):
    """매매 확인 클릭시 - 고정키보드 유지 + 인라인 버튼으로 폼 열기"""
    payload = {
        "chat_id": chat_id,
        "text": f"🟢 <b>MNQ V21 최종이용자 폼</b>\n\n아래 버튼을 클릭하여 매매를 확인하세요.\n\n📱 폼 주소: {FINAL_FORM_URL}\n시간: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📱 최종이용자 폼 열기", "url": FINAL_FORM_URL}],
                [{"text": "매매 확인", "callback_data": "check_trade"}]
            ]
        }
    }
    return tg_api("sendMessage", payload)

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
        "버전": "V21-BUTTON-FIXED",
        "telegram_token_set": bool(BOT_TOKEN),
        "channel": CHANNEL_ID,
        "final_form_url": FINAL_FORM_URL,
        "routes": ["/", "/health", "/api", "/api/history", "/api/test-telegram", "/api/setup-keyboard", "/telegram-webhook"]
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
    tg_resp = send_telegram_debug(tg_text, with_button=True)
    return jsonify({"ok": True, "received": latest_signal, "telegram_response": tg_resp})

@app.route("/api/history")
def api_history():
    return jsonify(history[-20:])

@app.route("/api/test-telegram")
def test_telegram():
    msg = f"✅ MNQ V21 테스트 - {time.strftime('%Y-%m-%d %H:%M:%S')}\n서버: mnq-v21-server-jxdu\n<a href=\"{FINAL_FORM_URL}\">최종이용자 폼</a>"
    resp = send_telegram_debug(msg, with_button=True)
    return jsonify({
        "ok": resp.get("ok", False),
        "channel": CHANNEL_ID,
        "final_form_url": FINAL_FORM_URL,
        "telegram_full_response": resp
    })

@app.route("/api/set-webhook")
def set_webhook():
    """텔레그램 봇 웹훅 설정 - 매매 확인 버튼 작동에 필요"""
    webhook_url = f"https://{request.host}/telegram-webhook"
    resp = tg_api("setWebhook", {"url": webhook_url})
    info = tg_api("getWebhookInfo", {})
    return jsonify({
        "ok": resp.get("ok", False),
        "setWebhook_response": resp,
        "webhookInfo": info,
        "webhook_url": webhook_url,
        "next": "텔레그램에서 @mnq_signal_2026_bot 에게 /start 입력하면 하단에 '매매 확인' 버튼 생성됨"
    })

@app.route("/api/setup-keyboard", methods=["GET","POST"])
def setup_keyboard():
    """그림처럼 '매매 확인' 고정 버튼 생성 - 채널에 고정 메시지 + 봇 웹훅 설정"""
    # 1. 채널에 고정용 메시지 전송 (인라인 버튼 포함)
    fixed_msg = f"""🟢 <b>MNQ V21 최종이용자 폼 - 고정 메시지</b>

📱 <b>매매 확인하려면 아래 버튼 클릭</b>

폼 주소: {FINAL_FORM_URL}
채널: {CHANNEL_ID}
시간: {time.strftime('%Y-%m-%d %H:%M:%S')}

<code>클릭 → 매매 확인</code>"""
    resp1 = send_telegram_debug(fixed_msg, with_button=True)
    
    # 2. 웹훅 URL 설정 안내
    webhook_url = f"https://{request.host}/telegram-webhook"
    return jsonify({
        "ok": True,
        "fixed_message_response": resp1,
        "final_form_url": FINAL_FORM_URL,
        "webhook_url_to_set": webhook_url,
        "next_step": f"브라우저에서 https://api.telegram.org/bot{BOT_TOKEN[:10]}.../setWebhook?url={webhook_url} 호출하여 웹훅 설정 후 /start 입력하면 그림처럼 '매매 확인' 버튼 생성됨",
        "manual_test": f"/telegram-webhook 에 POST로 /start 보내면 고정키보드 생성됨"
    })

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    """텔레그램 봇 웹훅 - /start, '매매 확인' 처리하여 그림처럼 버튼 생성"""
    data = request.get_json(force=True, silent=True) or {}
    print(f"[WEBHOOK] {data}")
    
    # Callback query (인라인 버튼 클릭)
    if "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        if cb.get("data") == "check_trade":
            # 매매 확인 콜백 -> 폼 링크 전송
            send_form_with_both(chat_id)
            # callback 응답
            tg_api("answerCallbackQuery", {"callback_query_id": cb["id"], "text": "매매 확인 - 폼을 열어주세요"})
        return jsonify({"ok": True})

    # 일반 메시지
    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        
        if text == "/start":
            welcome = f"""🟢 <b>MNQ Signal Bot</b>

안녕하세요! MNQ V21 신호봇입니다.

하단 <b>'매매 확인'</b> 버튼을 누르면 최종이용자 폼이 열립니다.

📱 폼: {FINAL_FORM_URL}
채널: {CHANNEL_ID}

명령어:
/start - 시작 및 버튼 생성
/form - 폼 바로 열기
"""
            send_with_fixed_keyboard(chat_id, welcome)
            return jsonify({"ok": True, "action": "sent_welcome_with_keyboard"})
        
        elif text == "매매 확인" or text == "/form":
            send_form_with_both(chat_id)
            return jsonify({"ok": True, "action": "sent_form"})
        
        elif "/form" in text or "/매매" in text:
            send_form_with_both(chat_id)
            return jsonify({"ok": True, "action": "sent_form_alias"})
    
    return jsonify({"ok": True, "ignored": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
