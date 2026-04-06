#
# webhook_server.py: Webhook receiver for degirum_events emissions
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Receives POST /events from the WebhookConnector in degirum_events.
# Stores emissions in memory and exposes them via GET /events.
#
# Run:
#   python webhook_server.py
#
# Emission payload format (sent by degirum_events WebhookConnector):
#   {
#     "trigger_id": "queue_overflow",
#     "payload":    {...},           # metric values and metadata
#     "severity":   "warning",       # info | warning | error
#     "firing":     "rising",        # rising | falling | scheduled | occurrence
#     "timestamp":  1712145600.5     # Unix epoch seconds
#   }
#

from flask import Flask, request, jsonify

app = Flask(__name__)
_emissions: list[dict] = []


@app.route("/events", methods=["POST"])
def receive():
    """Receive an emission from degirum_events WebhookConnector."""
    emission = request.get_json(force=True, silent=True) or {}
    _emissions.append(emission)
    print(
        f"  [{emission.get('severity', '?').upper()}]"
        f" {emission.get('trigger_id', '?')}"
        f" | {emission.get('firing', '?')}"
        f" | {emission.get('payload', {})}"
    )
    return jsonify({"acknowledged": True})


@app.route("/events", methods=["GET"])
def get_events():
    """Return all received emissions."""
    return jsonify({"emissions": _emissions, "count": len(_emissions)})


@app.route("/events/clear", methods=["POST"])
def clear():
    """Clear the in-memory emission store."""
    _emissions.clear()
    return jsonify({"cleared": True})


if __name__ == "__main__":
    print("Webhook receiver listening on http://localhost:5001")
    print("  POST /events       — receive emissions from degirum_events")
    print("  GET  /events       — fetch all received emissions")
    print("  POST /events/clear — clear stored emissions")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5001, debug=False)
