
"""
텔레그램 모바일용 - 최종이용자 핸드폰에서 Qqq List Final Registered 폼이 보이게 하는 봇

핵심: PC 화면이 아니라 최종이용자가 핸드폰 텔레그램으로 접속했을 때 이 화면이 보여야 함
"""

import os
import json
import requests
from datetime import datetime

BOT_TOKEN = "8846428557:AAHU26IX9tQFdyNVHCaCkfcJw0HAc1ZCn2E"
CHANNEL_ID = "-1004340608403"

FIXED_FORM_DATA = {
    "symbol": "MNQM26",
    "user": "한규리",
    "total_asset": "$2,111,184",
    "daily_profit": "+$2,153.50",
    "status": "접속중",
    "profit_rate": "62.1%"
}

def check_bot_token():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        r = requests.get(url, timeout=10)
        print(f"[Token Check] {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"✅ Bot valid: @{data['result']['username']}")
            return True
        else:
            print(f"❌ Token invalid: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Token check error: {e}")
        return False

def send_final_form_to_telegram_mobile():
    message = f"""📊 Qqq List - 최종이용자 고정폼

👤 {FIXED_FORM_DATA['user']} | {FIXED_FORM_DATA['status']}
📌 {FIXED_FORM_DATA['symbol']}

💰 총 자산: {FIXED_FORM_DATA['total_asset']}
   오늘 수익: {FIXED_FORM_DATA['daily_profit']}

📈 수익률: {FIXED_FORM_DATA['profit_rate']} 달성 (목표 $3.4M)
   ██████░░░░ 62.1%

⏰ {datetime.now().strftime('%m/%d %H:%M:%S')} KST

━━━━━━━━━━━━━━━━━━━━
⬇️ 아래 버튼을 누르면 Qqq List 폼이 핸드폰에서 열립니다
"""

    WEB_APP_URL = "https://mnq-v21-server.onrender.com/final_form"
    
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "매매창 열기", "web_app": {"url": WEB_APP_URL}},
                {"text": "💰 수익 보기", "callback_data": "profit"}
            ],
            [
                {"text": "초기화면", "callback_data": "home"},
                {"text": "매매중지", "callback_data": "stop"},
                {"text": "종목선택", "callback_data": "symbol"}
            ]
        ]
    }
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "reply_markup": inline_keyboard
    }
    
    try:
        print(f"[Telegram Mobile] 채널 {CHANNEL_ID}로 전송...")
        r = requests.post(url, json=payload, timeout=10)
        print(f"Response: {r.status_code} {r.text[:500]}")
        if r.status_code == 200:
            print(f"✅ 성공 - 이제 최종이용자 핸드폰 텔레그램에서 Qqq List 폼이 보입니다")
            return True
        else:
            print(f"❌ 실패")
            return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

if __name__ == "__main__":
    print("="*70)
    print("텔레그램 모바일용 Qqq List Final Registered 폼 전송")
    print("PC가 아니라 최종이용자 핸드폰 텔레그램에서 보여야 함")
    print("="*70)
    token_ok = check_bot_token()
    if token_ok:
        send_final_form_to_telegram_mobile()
    else:
        print("\n토큰 만료 시뮬레이션:")
        print("최종이용자 핸드폰에서는 아래와 같이 보입니다:")
        print(f"📊 Qqq List - {FIXED_FORM_DATA['total_asset']}")
        print("[초기화면] [수익] [매매중지] [종목선택]")
