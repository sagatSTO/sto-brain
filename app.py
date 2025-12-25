from flask import Flask, request, jsonify, render_template_string
import time
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
MODE = "OFFLINE"
MODE_DECISION = "C"   # A / B / C
CAPITAL_INITIAL = 1000.0

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "capital": CAPITAL_INITIAL,
    "position": None,   # None / LONG
    "last_price": None,
    "mode": MODE,
    "mode_decision": MODE_DECISION,
    "start_time": time.time()
}

# CACHE & JOURNAL
cache_market = {}
journal = []

# ======================
# INDICATEURS
# ======================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# ======================
# SIMULATION + PAPER
# ======================
@app.route("/simulate", methods=["GET"])
def simulate():
    raw = request.args.get("prices", "")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({
            "statut_marche": "ERREUR",
            "raison": "Pas assez de données simulées"
        })

    rsi = calculate_rsi(prices)
    ema_fast = calculate_ema(prices, 10)
    ema_slow = calculate_ema(prices, 20)
    price = prices[-1]

    action = "ATTENTE"

    # LOGIQUE MODE C
    if rsi and ema_fast and ema_slow:
        if rsi < 30 and ema_fast > ema_slow and sto_state["position"] is None:
            action = "BUY"
            sto_state["position"] = "LONG"
            sto_state["last_price"] = price
        elif rsi > 70 and sto_state["position"] == "LONG":
            action = "SELL"
            profit = price - sto_state["last_price"]
            sto_state["capital"] += profit
            sto_state["position"] = None

    # JOURNAL
    journal.append({
        "time": int(time.time()),
        "price": price,
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "action": action,
        "capital": round(sto_state["capital"], 2)
    })

    # CACHE
    cache_market["last"] = journal[-1]

    return jsonify({
        "mode": "PAPER",
        "action_STO": action,
        "prix_actuel": price,
        "RSI": rsi,
        "EMA_fast": ema_fast,
        "EMA_slow": ema_slow,
        "capital": round(sto_state["capital"], 2)
    })

# ======================
# JOURNAL API
# ======================
@app.route("/journal", methods=["GET"])
def get_journal():
    return jsonify(journal)

# ======================
# DASHBOARD
# ======================
@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>STO Dashboard</title>
        <style>
            body { background:#0e0e0e; color:#00ff99; font-family:Arial; }
            h1 { color:#00ffaa; }
            .box { margin:20px; }
        </style>
    </head>
    <body>
        <h1>STO Dashboard</h1>
        <div class="box">Mode : {{mode}}</div>
        <div class="box">Décision : {{decision}}</div>
        <div class="box">Capital : {{capital}}</div>
        <div class="box">Position : {{position}}</div>
        <div class="box">Journal entries : {{entries}}</div>
    </body>
    </html>
    """,
    mode=sto_state["mode"],
    decision=sto_state["mode_decision"],
    capital=sto_state["capital"],
    position=sto_state["position"],
    entries=len(journal)
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
