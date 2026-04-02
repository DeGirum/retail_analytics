#
# webhook_server.py: Flask server to receive retail analytics events
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Run: python webhook_server.py
# Receives POST /events from dwell_time_with_events_example.py
# GET /events returns collected events
# Appends all events to events.csv for LLM analysis
#

import csv
from pathlib import Path

from flask import Flask, request, jsonify

app = Flask(__name__)
events_store = []

CSV_PATH = Path(__file__).resolve().parent / "events.csv"
CSV_HEADERS = ["event_type", "timestamp", "zone_id", "track_id", "duration", "established_time", "current_occupancy", "max_capacity", "extra"]


def _flatten_event_to_row(data: dict) -> dict:
    """Flatten event payload to CSV row. For density_snapshot, emit one row per zone."""
    event_type = data.get("event_type", "unknown")
    payload = data.get("data", {})
    ts = payload.get("timestamp") or payload.get("established_time") or ""
    zone_id = payload.get("zone_id", "")
    track_id = payload.get("track_id", "")
    duration = payload.get("duration", "")
    established_time = payload.get("established_time", "")

    if event_type == "retail.zone.density_snapshot":
        stats = payload.get("stats", {})
        rows = []
        for z, s in stats.items():
            rows.append({
                "event_type": event_type,
                "timestamp": payload.get("timestamp", ts),
                "zone_id": z,
                "track_id": "",
                "duration": "",
                "established_time": "",
                "current_occupancy": s.get("current_occupancy", ""),
                "max_capacity": s.get("max_capacity", ""),
                "extra": "",
            })
        return rows
    else:
        return [{
            "event_type": event_type,
            "timestamp": ts,
            "zone_id": zone_id,
            "track_id": track_id,
            "duration": duration,
            "established_time": established_time,
            "current_occupancy": "",
            "max_capacity": "",
            "extra": "",
        }]


def _append_to_csv(data: dict) -> None:
    """Append flattened event(s) to CSV file."""
    rows = _flatten_event_to_row(data)
    file_exists = CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


@app.route("/events", methods=["POST"])
def receive_events():
    """Receive events from EventManager WebhookPlugin"""
    data = request.get_json(force=True, silent=True) or {}
    events_store.append(data)
    _append_to_csv(data)
    event_type = data.get("event_type", "unknown")
    payload = data.get("data", {})
    print(f"  [RECEIVED] {event_type} | zone={payload.get('zone_id')} track={payload.get('track_id')} duration={payload.get('duration', 0):.1f}s")
    return jsonify({"acknowledged": True, "delivered_to": 1})


@app.route("/events", methods=["GET"])
def get_events():
    """Return all collected events"""
    return jsonify({"events": events_store, "count": len(events_store)})


@app.route("/events/clear", methods=["POST"])
def clear_events():
    """Clear in-memory events (CSV is preserved for history)"""
    global events_store
    events_store = []
    return jsonify({"cleared": True})


@app.route("/events/csv_path", methods=["GET"])
def get_csv_path():
    """Return path to events CSV for dashboard"""
    return jsonify({"path": str(CSV_PATH), "exists": CSV_PATH.exists()})


def _ask_events_llm(question: str) -> str:
    """Load CSV, run pandas, call LLM. Used by /ask endpoint."""
    import os
    try:
        import pandas as pd
    except ImportError:
        return "Error: pandas not installed. pip install pandas"
    try:
        from openai import OpenAI
    except ImportError:
        return "Error: openai not installed. pip install openai"

    if not CSV_PATH.exists():
        return "No events data yet. Run analytics and generate some events first."

    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        return f"Error reading CSV: {e}"

    if df.empty or len(df) < 2:
        return "Not enough events to analyze. Run analytics longer to collect data."

    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
    df = df.dropna(subset=["datetime"])
    if df.empty:
        return "Could not parse timestamps in the data."

    stats_parts = []
    if "event_type" in df.columns:
        activity = df[df["event_type"].isin(["retail.zone.entered", "retail.zone.session_complete"])].copy()
        if not activity.empty:
            activity["hour"] = activity["datetime"].dt.hour
            hourly = activity.groupby("hour").size().reset_index(name="count")
            hourly = hourly.sort_values("count", ascending=False)
            stats_parts.append("Events per hour (busiest first):\n" + hourly.head(10).to_string(index=False))
    if "zone_id" in df.columns:
        zone_df = df[df["zone_id"].notna() & (df["zone_id"] != "")]
        if not zone_df.empty:
            zone_counts = zone_df.groupby("zone_id").size().reset_index(name="count")
            zone_counts = zone_counts.sort_values("count", ascending=False)
            stats_parts.append("Events per zone:\n" + zone_counts.to_string(index=False))
    duration_df = df[(df["event_type"] == "retail.zone.session_complete") & (df["duration"].notna())]
    if not duration_df.empty:
        duration_df = duration_df.copy()
        duration_df["duration"] = pd.to_numeric(duration_df["duration"], errors="coerce")
        duration_df = duration_df.dropna(subset=["duration"])
        if not duration_df.empty:
            stats_parts.append(
                f"Session durations: count={len(duration_df)}, "
                f"mean={duration_df['duration'].mean():.1f}s, max={duration_df['duration'].max():.1f}s"
            )
            if "zone_id" in duration_df.columns:
                zone_dwell = duration_df.groupby("zone_id")["duration"].agg(["mean", "count"]).round(1)
                stats_parts.append("Avg dwell time by zone:\n" + zone_dwell.to_string())
    density_df = df[df["event_type"] == "retail.zone.density_snapshot"]
    if not density_df.empty and "current_occupancy" in df.columns:
        density_df = density_df.copy()
        density_df["current_occupancy"] = pd.to_numeric(density_df["current_occupancy"], errors="coerce")
        density_df = density_df.dropna(subset=["current_occupancy"])
        if not density_df.empty:
            density_df["hour"] = density_df["datetime"].dt.hour
            hourly_occ = density_df.groupby("hour")["current_occupancy"].sum().reset_index()
            hourly_occ = hourly_occ.sort_values("current_occupancy", ascending=False)
            stats_parts.append("Total occupancy per hour:\n" + hourly_occ.head(10).to_string(index=False))
    stats_text = "\n\n".join(stats_parts) if stats_parts else f"Raw event count: {len(df)}"

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "OpenAI API key not set (OPENAI_API_KEY). Computed stats:\n\n" + stats_text

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a retail analytics assistant. Answer the user's question based on the provided event statistics. Be concise and specific."},
                {"role": "user", "content": f"Event statistics:\n\n{stats_text}\n\nQuestion: {question}"},
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content or "No response from LLM."
    except Exception as e:
        return f"LLM error: {e}\n\nComputed stats:\n\n{stats_text}"


@app.route("/ask", methods=["POST"])
def ask():
    """Analyze events CSV with pandas + LLM and answer the question"""
    data = request.get_json(force=True, silent=True) or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided."}), 400
    answer = _ask_events_llm(question)
    return jsonify({"answer": answer})


if __name__ == "__main__":
    print("Webhook server: http://localhost:5000")
    print("  POST /events - receive events")
    print("  GET  /events - fetch collected events")
    print("  POST /ask - analyze events.csv with LLM (needs pandas, openai, OPENAI_API_KEY)")
    print("  Events saved to:", CSV_PATH)
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
