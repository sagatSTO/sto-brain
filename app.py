from flask import Flask, request, jsonify
import time

app = Flask(__name__)

ADMIN_EMAIL = ADMIN_EMAIL =
"saguiorelio32@gmail.com"

sto_state = {
    "mode": "OBSERVATION",
    "market_status": "INCONNU",
    "last_action": "ATTENTE",
    "reason": "STO démarre",
    "start_time": time.time()
}

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "statut": "STO EN LIGNE",
        "mode": sto_state["mode"],
        "temps_en_ligne_secondes": int(time.time() - sto_state["start_time"])
    })

@app.route("/market/status", methods=["GET"])
def market_status():
    sto_state["market_status"] = "NEUTRE"
    sto_state["last_action"] = "ATTENTE"
    sto_state["reason"] = "Marché sans tendance claire"
    return jsonify(sto_state)

@app.route("/bot/action", methods=["GET"])
def bot_action():
    return jsonify({
        "action": sto_state["last_action"],
        "raison": sto_state["reason"],
        "mode": sto_state["mode"]
    })

@app.route("/auth/verify_qr", methods=["POST"])
def verify_qr():
    data = request.json
    email = data.get("email")
    if email == ADMIN_EMAIL:
        return jsonify({"acces": "admin"})
    return jsonify({"acces": "utilisateur"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
