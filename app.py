from flask import Flask, request, jsonify
import time, uuid
from statistics import mean

app = Flask(__name__)

# ======================
# CONFIG
# ======================
MODE_DECISION = "C"
MODE_EXECUTION = "PAPER"

CAPITAL_INITIAL = 1000.0
RISQUE_PAR_TRADE = 0.02          # 2%
TP_POURCENT = 0.03               # +3%
SL_POURCENT = 0.015              # -1.5%
SEUIL_JOURNALIER = 5
CONFIRMATION_REQUIRED = 2

# ======================
# TABLES
# ======================
DECISION_JOURNAL = []
PAPER_TRADES = []

# ======================
# ÉTAT GLOBAL
# ======================
sto_state = {
    "capital": CAPITAL_INITIAL,
    "open_position": None,
    "daily_count": 0,
    "last_reset": time.strftime("%Y-%m-%d"),
    "signal_history": [],
    "start_time": time.time()
}

# ======================
# UTILS
# ======================
def reset_daily():
    today = time.strftime("%Y-%m-%d")
    if sto_state["last_reset"] != today:
        sto_state["daily_count"] = 0
        sto_state["last_reset"] = today

def rsi(prices, p=14):
    if len(prices) < p + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d,0))
        losses.append(abs(min(d,0)))
    ag, al = mean(gains[:p]), mean(losses[:p])
    if al == 0:
        return 100
    return round(100 - (100 / (1 + ag/al)),2)

def ema(prices, p):
    if len(prices) < p:
        return None
    k = 2/(p+1)
    e = prices[0]
    for x in prices[1:]:
        e = x*k + e*(1-k)
    return round(e,2)

def position_size(capital, price):
    return round((capital * RISQUE_PAR_TRADE) / price, 6)

def confirm(signal):
    h = sto_state["signal_history"]
    h.append(signal)
    if len(h) > 5:
        h.pop(0)
    return h.count(signal) >= CONFIRMATION_REQUIRED

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return jsonify({
        "statut": "STO OPÉRATIONNEL",
        "mode_execution": MODE_EXECUTION,
        "capital": round(sto_state["capital"],2),
        "position": sto_state["open_position"]
    })

@app.route("/simulate")
def simulate():
    reset_daily()
    raw = request.args.get("prices","")
    prices = [float(x) for x in raw.split(",") if x.strip()]

    if len(prices) < 20:
        return jsonify({"erreur":"Pas assez de données"})

    price = prices[-1]
    r = rsi(prices)
    ef, es = ema(prices,10), ema(prices,20)

    signal = "ATTENTE"
    if r and ef and es:
        if r > 60 and ef > es:
            signal = "ACHAT"
        elif r < 40 and ef < es:
            signal = "VENTE"

    confirmed = confirm(signal)
    trade_closed = None

    pos = sto_state["open_position"]

    # ===== OUVERTURE POSITION =====
    if confirmed and pos is None and signal == "ACHAT":
        qty = position_size(sto_state["capital"], price)
        sto_state["open_position"] = {
            "type": "LONG",
            "entry": price,
            "qty": qty,
            "tp": round(price * (1 + TP_POURCENT),2),
            "sl": round(price * (1 - SL_POURCENT),2),
            "time": int(time.time())
        }

    # ===== GESTION TP / SL =====
    elif pos:
        if price >= pos["tp"] or price <= pos["sl"]:
            pnl = (price - pos["entry"]) * pos["qty"]
            sto_state["capital"] += pnl
            trade_closed = round(pnl,2)

            PAPER_TRADES.append({
                "id": str(uuid.uuid4()),
                "entry": pos["entry"],
                "exit": price,
                "qty": pos["qty"],
                "pnl": round(pnl,2),
                "timestamp": int(time.time())
            })

            sto_state["open_position"] = None

    DECISION_JOURNAL.append({
        "signal": signal,
        "confirmé": confirmed,
        "prix": price,
        "time": int(time.time())
    })

    return jsonify({
        "signal": signal,
        "confirmé": confirmed,
        "rsi": r,
        "ema_fast": ef,
        "ema_slow": es,
        "position": sto_state["open_position"],
        "pnl_trade": trade_closed,
        "capital": round(sto_state["capital"],2),
        "mode_execution": MODE_EXECUTION
    })

@app.route("/paper_trades")
def paper_trades():
    return jsonify(PAPER_TRADES[-20:])

@app.route("/journal")
def journal():
    return jsonify(DECISION_JOURNAL[-20:])

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
