
from flask import Flask, Response, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

HOLDINGS_FILE = "holdings.json"

def load_holdings():
    if os.path.exists(HOLDINGS_FILE):
        try:
            with open(HOLDINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return [
        {"symbol": "MNQM26", "name": "Micro Nasdaq M26", "qty": 2, "avgPrice": 21200, "currentPrice": 21450, "profit": "+$500"},
        {"symbol": "AAPL", "name": "Apple Inc", "qty": 10, "avgPrice": 210, "currentPrice": 215, "profit": "+$50"}
    ]

def save_holdings(holdings):
    holdings = holdings[:5]
    try:
        with open(HOLDINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(holdings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save error: {e}")
    return holdings

@app.route('/final_form')
def final_form():
    """Qqq List - 최종이용자 고정폼 - 종목선택 5개 (매매창 열기) - 텔레그램 핸드폰용"""
    for path in ["Qqq_List_Final_Registered.html", "final_form_5stocks_completed.html", "최종이용자_종목선택_5개_완성.html"]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return Response(f.read(), mimetype='text/html')
    return "Final form not found", 404

@app.route('/api/holdings', methods=['GET', 'POST'])
def holdings_api():
    if request.method == 'GET':
        holdings = load_holdings()
        return jsonify({"holdings": holdings, "count": len(holdings), "max": 5, "timestamp": datetime.now().isoformat()})
    else:
        data = request.json
        holdings = data.get('holdings', [])
        saved = save_holdings(holdings)
        return jsonify({"status": "saved", "holdings": saved, "count": len(saved)})

@app.route('/api/holdings/add', methods=['POST'])
def holdings_add():
    data = request.json
    symbol_input = data.get('symbol', '').strip().upper()
    if not symbol_input:
        return jsonify({"error": "종목명 또는 번호 필요"}), 400
    holdings = load_holdings()
    if len(holdings) >= 5:
        return jsonify({"error": "최대 5개까지만 보유 가능", "holdings": holdings}), 400
    symbol_map = {
        "005930": {"symbol": "005930", "name": "삼성전자"},
        "000660": {"symbol": "000660", "name": "SK하이닉스"},
        "035420": {"symbol": "035420", "name": "NAVER"},
        "AAPL": {"symbol": "AAPL", "name": "Apple Inc"},
        "TSLA": {"symbol": "TSLA", "name": "Tesla"},
        "NVDA": {"symbol": "NVDA", "name": "NVIDIA"},
        "MNQM26": {"symbol": "MNQM26", "name": "Micro Nasdaq M26"},
        "MNQU26": {"symbol": "MNQU26", "name": "Micro Nasdaq U26"},
        "MNQZ26": {"symbol": "MNQZ26", "name": "Micro Nasdaq Z26"}
    }
    mapped = symbol_map.get(symbol_input, {"symbol": symbol_input, "name": symbol_input})
    if any(h['symbol'] == mapped['symbol'] for h in holdings):
        return jsonify({"error": f"{mapped['symbol']} 이미 보유 중", "holdings": holdings}), 400
    new_holding = {
        "symbol": mapped['symbol'],
        "name": mapped['name'],
        "qty": 1,
        "avgPrice": 20000,
        "currentPrice": 20500,
        "profit": "+$100",
        "added_at": datetime.now().isoformat(),
        "source": data.get('source', 'pc')
    }
    holdings.append(new_holding)
    saved = save_holdings(holdings)
    return jsonify({"status": "added", "holding": new_holding, "holdings": saved})

@app.route('/api/holdings/remove/<symbol>', methods=['DELETE'])
def holdings_remove(symbol):
    holdings = load_holdings()
    holdings = [h for h in holdings if h['symbol'] != symbol.upper()]
    saved = save_holdings(holdings)
    return jsonify({"status": "removed", "holdings": saved})

@app.route('/api/telegram_notify', methods=['POST'])
def telegram_notify():
    data = request.json
    print(f"[Telegram Notify] {data}")
    return jsonify({"status": "notified"})

@app.route('/api/signal', methods=['GET', 'POST'])
def signal():
    if request.method == 'GET':
        client_id = request.args.get('client_id')
        holdings = load_holdings()
        return jsonify({"status": "ok", "client_id": client_id, "symbol": "MNQM26", "holdings": holdings})
    else:
        data = request.json
        return jsonify({"status": "received", "signal_id": "123"})

@app.route('/')
def index():
    holdings = load_holdings()
    return f"""
    <h1>MNQ V21 Server - 최종이용자 종목선택 5개 완성</h1>
    <ul>
        <li><a href='/final_form'>매매창 열기 - Qqq List Final Registered (핸드폰 텔레그램용)</a></li>
        <li><a href='/api/holdings'>/api/holdings - 보유 종목 {len(holdings)}/5</a></li>
    </ul>
    <p>Telegram: -1004340608403 | Button: 매매창 열기 -> /final_form</p>
    <p>보유: PC 매수 종목 + 텔레그램 종목선택 추가 (최대 5개) | 종목명/번호 입력으로 매수</p>
    <p>Holdings: {', '.join([h['symbol'] for h in holdings])}</p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
