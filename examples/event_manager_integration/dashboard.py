#
# dashboard.py: NiceGUI Dashboard for Retail Analytics Events
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Run: python dashboard.py
# Requires: nicegui, requests, plotly
# Start webhook_server.py first. Use the Control Panel to start analytics.
#

import sys
import subprocess
import threading
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Project root (retail_analytics)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

EXAMPLES_DIR = Path(__file__).resolve().parent.parent
INTEGRATION_DIR = Path(__file__).resolve().parent

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. pip install requests")
    sys.exit(1)

try:
    from nicegui import ui
except ImportError:
    print("ERROR: nicegui not installed. pip install nicegui")
    sys.exit(1)

try:
    import plotly.graph_objects as go
except ImportError:
    print("ERROR: plotly not installed. pip install plotly")
    sys.exit(1)

WEBHOOK_URL = "http://localhost:5000"
POLL_INTERVAL = 2.0

# Analytics subprocesses: {analyzer_type: Popen}
_analytics_processes = {}


def fetch_events():
    """Fetch events from webhook server"""
    try:
        r = requests.get(f"{WEBHOOK_URL}/events", timeout=5)
        r.raise_for_status()
        return r.json().get("events", [])
    except requests.exceptions.ConnectionError:
        return None
    except Exception:
        return None


def clear_events():
    """Clear events on webhook server"""
    try:
        requests.post(f"{WEBHOOK_URL}/events/clear", timeout=5)
    except Exception:
        pass


def load_config(analyzer_type: str) -> dict:
    """Load config YAML for analyzer type"""
    if analyzer_type == "zone_density":
        path = EXAMPLES_DIR / "zone_density_config.yaml"
    else:
        path = EXAMPLES_DIR / "dwell_time_config.yaml"
    if path.exists():
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(analyzer_type: str, config: dict) -> None:
    """Save config YAML"""
    if analyzer_type == "zone_density":
        path = EXAMPLES_DIR / "zone_density_config.yaml"
    else:
        path = EXAMPLES_DIR / "dwell_time_config.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def start_analytics(
    selected_analyzers: list,
    video_source: str,
    snapshot_interval: float,
    min_duration: float,
) -> bool:
    """Start analytics subprocesses for selected analyzers. Returns True if any started."""
    global _analytics_processes
    if not selected_analyzers:
        return False

    started = False
    for analyzer_type in selected_analyzers:
        if analyzer_type in _analytics_processes and _analytics_processes[analyzer_type].poll() is None:
            continue  # Already running

        if analyzer_type == "zone_density":
            script = INTEGRATION_DIR / "density_with_events_example.py"
            args = [sys.executable, str(script)]
            if video_source:
                args.append(video_source)
            args.append(str(snapshot_interval))
        else:
            script = INTEGRATION_DIR / "dwell_time_with_events_example.py"
            args = [sys.executable, str(script)]
            if video_source:
                args.append(video_source)

        config = load_config(analyzer_type)
        if video_source:
            try:
                config["video_source"] = int(video_source)
            except ValueError:
                config["video_source"] = video_source
        if analyzer_type == "zone_density":
            for a in config.get("analyzers", []):
                if a.get("type") == "zone_density" and "config" in a:
                    a["config"]["snapshot_interval_seconds"] = snapshot_interval
                    break
        else:
            for a in config.get("analyzers", []):
                if a.get("type") == "dwell_time" and "config" in a:
                    a["config"]["min_duration"] = min_duration
                    break
        save_config(analyzer_type, config)

        _analytics_processes[analyzer_type] = subprocess.Popen(
            args,
            cwd=str(INTEGRATION_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        started = True
    return started


def stop_analytics() -> bool:
    """Stop all analytics subprocesses. Returns True if any was running."""
    global _analytics_processes
    was_running = False
    for key in list(_analytics_processes.keys()):
        proc = _analytics_processes[key]
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            was_running = True
        del _analytics_processes[key]
    return was_running


def is_analytics_running() -> bool:
    """Check if any analytics subprocess is running"""
    global _analytics_processes
    return any(p.poll() is None for p in _analytics_processes.values())


def ask_events_llm(question: str) -> str:
    """
    Load events CSV, run pandas aggregations, and use LLM to answer the question.
    Returns answer string or error message.
    """
    import os
    try:
        import pandas as pd
    except ImportError:
        return "Error: pandas not installed. pip install pandas"
    try:
        from openai import OpenAI
    except ImportError:
        return "Error: openai not installed. pip install openai"

    if not EVENTS_CSV_PATH.exists():
        return "No events data yet. Run analytics and generate some events first."

    try:
        df = pd.read_csv(EVENTS_CSV_PATH)
    except Exception as e:
        return f"Error reading CSV: {e}"

    if df.empty or len(df) < 2:
        return "Not enough events to analyze. Run analytics longer to collect data."

    # Parse timestamps
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
    df = df.dropna(subset=["datetime"])
    if df.empty:
        return "Could not parse timestamps in the data."

    # Build stats summary with pandas
    stats_parts = []

    # Hourly activity (entries + exits)
    if "event_type" in df.columns:
        activity = df[df["event_type"].isin(["retail.zone.entered", "retail.zone.session_complete"])].copy()
        if not activity.empty:
            activity["hour"] = activity["datetime"].dt.hour
            hourly = activity.groupby("hour").size().reset_index(name="count")
            hourly = hourly.sort_values("count", ascending=False)
            stats_parts.append("Events per hour (busiest first):\n" + hourly.head(10).to_string(index=False))

    # Zone stats
    if "zone_id" in df.columns:
        zone_df = df[df["zone_id"].notna() & (df["zone_id"] != "")]
        if not zone_df.empty:
            zone_counts = zone_df.groupby("zone_id").size().reset_index(name="count")
            zone_counts = zone_counts.sort_values("count", ascending=False)
            stats_parts.append("Events per zone:\n" + zone_counts.to_string(index=False))

    # Duration stats (session_complete)
    duration_df = df[(df["event_type"] == "retail.zone.session_complete") & (df["duration"].notna())]
    if not duration_df.empty:
        duration_df = duration_df.copy()
        duration_df["duration"] = pd.to_numeric(duration_df["duration"], errors="coerce")
        duration_df = duration_df.dropna(subset=["duration"])
        if not duration_df.empty:
            stats_parts.append(
                f"Session durations: count={len(duration_df)}, "
                f"mean={duration_df['duration'].mean():.1f}s, "
                f"max={duration_df['duration'].max():.1f}s"
            )
            if "zone_id" in duration_df.columns:
                zone_dwell = duration_df.groupby("zone_id")["duration"].agg(["mean", "count"]).round(1)
                stats_parts.append("Avg dwell time by zone:\n" + zone_dwell.to_string())

    # Density snapshots
    density_df = df[df["event_type"] == "retail.zone.density_snapshot"]
    if not density_df.empty and "current_occupancy" in df.columns:
        density_df = density_df.copy()
        density_df["current_occupancy"] = pd.to_numeric(density_df["current_occupancy"], errors="coerce")
        density_df = density_df.dropna(subset=["current_occupancy"])
        if not density_df.empty:
            density_df["hour"] = density_df["datetime"].dt.hour
            hourly_occ = density_df.groupby("hour")["current_occupancy"].sum().reset_index()
            hourly_occ = hourly_occ.sort_values("current_occupancy", ascending=False)
            stats_parts.append("Total occupancy per hour (from density snapshots):\n" + hourly_occ.head(10).to_string(index=False))

    stats_text = "\n\n".join(stats_parts) if stats_parts else "Raw event count: " + str(len(df))

    # Call LLM
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return (
            "OpenAI API key not set. Set OPENAI_API_KEY environment variable.\n\n"
            "Computed stats (without LLM):\n\n" + stats_text
        )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a retail analytics assistant. Answer the user's question based on the provided event statistics. Be concise and specific. If the data doesn't support an answer, say so.",
                },
                {
                    "role": "user",
                    "content": f"Event statistics from retail analytics CSV:\n\n{stats_text}\n\nQuestion: {question}",
                },
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content or "No response from LLM."
    except Exception as e:
        return f"LLM error: {e}\n\nComputed stats:\n\n{stats_text}"


def _safe_str(val, default="-"):
    """Convert value to string for table display"""
    if val is None or val == "":
        return default
    return str(val)


def _derive_occupancy_from_dwell_events(events):
    """Build occupancy time series from entered/session_complete events (dwell time analyzer)."""
    # Collect events with timestamps, sort by time
    timeline = []
    for evt in events:
        etype = evt.get("event_type", "?")
        data = evt.get("data", {})
        ts = data.get("timestamp") or data.get("established_time") or evt.get("timestamp") or 0
        zone_id = data.get("zone_id", "")
        if etype == "retail.zone.entered" and zone_id:
            timeline.append((ts, "enter", zone_id))
        elif etype == "retail.zone.session_complete" and zone_id:
            timeline.append((ts, "exit", zone_id))
    timeline.sort(key=lambda x: x[0])

    occupancy = defaultdict(int)
    density_history = []
    for ts, action, zone_id in timeline:
        if action == "enter":
            occupancy[zone_id] += 1
        else:
            occupancy[zone_id] = max(0, occupancy[zone_id] - 1)
        density_history.append((ts, dict(occupancy)))
    return density_history


def process_events(events):
    """Process events into structures for charts and tables"""
    entries = []
    sessions = []  # session_complete
    density_history = []  # [(timestamp, {zone: occupancy}), ...]
    latest_density = {}  # {zone: {current_occupancy, max_capacity}}
    all_events_table = []
    row_id = 0

    for evt in events:
        etype = evt.get("event_type", "?")
        data = evt.get("data", {})
        ts = data.get("timestamp") or data.get("established_time") or evt.get("timestamp") or 0

        if etype == "retail.zone.entered":
            track_id = data.get("track_id")
            entries.append({
                "time": ts,
                "zone_id": data.get("zone_id", ""),
                "track_id": track_id,
            })
            row_id += 1
            all_events_table.append({
                "id": str(row_id),
                "event_type": "Entry",
                "zone": _safe_str(data.get("zone_id")),
                "track_id": _safe_str(track_id),
                "duration_s": "-",
                "timestamp": _format_ts(ts),
            })
        elif etype == "retail.zone.session_complete":
            dur = data.get("duration", 0)
            track_id = data.get("track_id")
            sessions.append({
                "zone_id": data.get("zone_id", ""),
                "track_id": track_id,
                "duration": dur,
                "timestamp": ts,
            })
            row_id += 1
            dur_str = f"{dur:.1f}" if isinstance(dur, (int, float)) else "-"
            all_events_table.append({
                "id": str(row_id),
                "event_type": "Exit",
                "zone": _safe_str(data.get("zone_id")),
                "track_id": _safe_str(track_id),
                "duration_s": dur_str,
                "timestamp": _format_ts(ts),
            })
        elif etype == "retail.zone.density_snapshot":
            stats = data.get("stats", {})
            if stats:
                occ = {z: s.get("current_occupancy", 0) for z, s in stats.items()}
                density_history.append((ts, occ))
                latest_density = stats
            row_id += 1
            all_events_table.append({
                "id": str(row_id),
                "event_type": "Density",
                "zone": ", ".join(stats.keys()) if stats else "-",
                "track_id": "-",
                "duration_s": "-",
                "timestamp": _format_ts(data.get("timestamp", ts)),
            })

    # If no density snapshots but we have dwell events, derive occupancy from entry/exit
    if not density_history and (entries or sessions):
        density_history = _derive_occupancy_from_dwell_events(events)
        if density_history:
            last_ts, last_occ = density_history[-1]
            latest_density = {
                z: {"current_occupancy": c, "max_capacity": None}
                for z, c in last_occ.items()
            }

    # Dwell summary by zone
    dwell_summary = defaultdict(list)
    for s in sessions:
        dwell_summary[s["zone_id"]].append(s["duration"])
    dwell_rows = [
        {
            "zone": zone,
            "count": len(durs),
            "avg_duration_s": f"{sum(durs) / len(durs):.1f}" if durs else "0",
        }
        for zone, durs in sorted(dwell_summary.items())
    ]

    # Track ID vs duration for bar chart (last 30 sessions, newest last)
    track_durations = [
        {"track_id": s["track_id"], "duration": s["duration"], "zone": s["zone_id"]}
        for s in sessions
    ][-30:]

    return {
        "entries": entries,
        "sessions": sessions,
        "density_history": density_history,
        "latest_density": latest_density,
        "all_events_table": list(reversed(all_events_table)),  # newest first
        "dwell_rows": dwell_rows,
        "track_durations": track_durations,
    }


def _format_ts(ts):
    if ts is None:
        return "-"
    try:
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except (TypeError, OSError):
        return str(ts)


def update_occupancy_chart(fig, density_history):
    """Update occupancy line chart in place. X-axis: seconds from first snapshot."""
    fig.data = []
    if not density_history:
        fig.add_annotation(text="No density data yet", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16))
    else:
        zones = sorted({z for _, occ in density_history for z in occ.keys()})
        times = [t for t, occ in density_history]
        t0 = times[0] if times else 0
        seconds_from_start = [t - t0 for t in times]
        for zone in zones:
            values = [occ.get(zone, 0) for _, occ in density_history]
            fig.add_trace(go.Scatter(x=seconds_from_start, y=values, mode="lines+markers", name=zone))
    fig.update_layout(
        title="Occupancy Over Time",
        xaxis_title="Seconds",
        yaxis_title="Count",
        height=250,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def update_track_duration_chart(fig, track_durations):
    """Update bar chart of track ID vs duration. Updates dynamically as sessions complete."""
    fig.data = []
    if hasattr(fig, "layout") and fig.layout.annotations:
        fig.layout.annotations = []
    if not track_durations:
        fig.add_annotation(text="No session data yet (run Dwell Time analyzer)", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    else:
        labels = []
        durations = []
        for d in track_durations:
            tid = d.get("track_id")
            dur = d.get("duration")
            try:
                dur_val = float(dur) if dur is not None else 0.0
                if dur_val >= 0:
                    labels.append(f"Track {tid}" + (f" ({d.get('zone', '')})" if d.get("zone") else ""))
                    durations.append(dur_val)
            except (TypeError, ValueError):
                pass
        if labels and durations:
            fig.add_trace(go.Bar(y=labels, x=durations, orientation="h", marker_color="teal", name="Duration"))
        else:
            fig.add_annotation(text="No valid session data yet", xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False, font=dict(size=14))
    fig.update_layout(
        title="Track ID vs Duration (s)",
        xaxis_title="Duration (s)",
        yaxis_title="Track",
        height=250,
        margin=dict(l=80, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def update_density_bar_chart(fig, latest_density):
    """Update density bar chart in place"""
    fig.data = []
    if not latest_density:
        fig.add_annotation(text="No density data yet", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16))
    else:
        zones = list(latest_density.keys())
        current = [latest_density[z].get("current_occupancy", 0) for z in zones]
        max_cap = [latest_density[z].get("max_capacity") or 0 for z in zones]
        fig.add_trace(go.Bar(name="Current", x=zones, y=current, marker_color="steelblue"))
        if any(max_cap):
            fig.add_trace(go.Bar(name="Max capacity", x=zones, y=max_cap,
                                 marker_color="lightgray", opacity=0.6))
    fig.update_layout(
        title="Current Zone Density",
        xaxis_title="Zone",
        yaxis_title="Count",
        barmode="overlay",
        height=250,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


@ui.page("/")
def main_page():
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1">')
    ui.colors(primary="#1976d2", secondary="#424242")

    with ui.header().classes("bg-primary text-white"):
        ui.label("Retail Analytics Dashboard").classes("text-h4 font-bold")
        ui.space()
        status = ui.label("Connecting...").classes("text-caption")
        ui.button("Clear events", on_click=lambda: (clear_events(), events_content())).props("flat")

    # Control panel
    with ui.card().classes("w-full m-4"):
        ui.label("Control Panel").classes("text-h6")
        with ui.row().classes("gap-4 flex-wrap"):
            ui.label("Analyzers:").classes("self-center")
            dwell_check = ui.checkbox("Dwell Time", value=False)
            density_check = ui.checkbox("Zone Density", value=True)
            video_input = ui.input(
                label="Video source",
                placeholder="0 for webcam, or path to video",
                value="0",
            ).classes("w-48")
            snapshot_input = ui.number(
                label="Snapshot interval (s)",
                value=5.0,
            ).classes("w-40")
            min_duration_input = ui.number(
                label="Min duration (s)",
                value=2.0,
            ).classes("w-40")

            start_btn = ui.button("Start analytics")
            clear_btn = ui.button("Clear", on_click=lambda: (clear_events(), events_content())).props("outline")
            stop_btn = ui.button("Stop analytics")
            analytics_status = ui.label("").classes("text-caption")

            def do_start():
                selected = []
                if dwell_check.value:
                    selected.append("dwell_time")
                if density_check.value:
                    selected.append("zone_density")
                if not selected:
                    ui.notify("Select at least one analyzer", type="warning")
                    return
                video = (video_input.value or "0").strip()
                snapshot = float(snapshot_input.value or 5)
                min_dur = float(min_duration_input.value or 2)
                if start_analytics(selected, video, snapshot, min_dur):
                    analytics_status.set_text("Running")
                    start_btn.set_visibility(False)
                    stop_btn.set_visibility(True)
                    ui.notify("Analytics started", type="positive")
                else:
                    ui.notify("Analytics already running", type="warning")

            def do_stop():
                if stop_analytics():
                    analytics_status.set_text("Stopped")
                    start_btn.set_visibility(True)
                    stop_btn.set_visibility(False)
                    ui.notify("Analytics stopped", type="info")
                else:
                    ui.notify("Analytics not running", type="info")

            start_btn.on("click", do_start)
            stop_btn.on("click", do_stop)
            stop_btn.set_visibility(False)

            def check_analytics_status():
                if not is_analytics_running() and analytics_status.text == "Running":
                    analytics_status.set_text("Stopped")
                    start_btn.set_visibility(True)
                    stop_btn.set_visibility(False)

            ui.timer(2.0, check_analytics_status)

    with ui.row().classes("w-full p-4 gap-4"):
        # Left column: charts
        with ui.column().classes("flex-1 min-w-0"):
            with ui.card().classes("w-full"):
                ui.label("Occupancy Over Time").classes("text-h6")
                fig_occupancy = go.Figure()
                update_occupancy_chart(fig_occupancy, [])
                occupancy_chart = ui.plotly(fig_occupancy).classes("w-full")
            with ui.card().classes("w-full"):
                ui.label("Current Zone Density").classes("text-h6")
                fig_density = go.Figure()
                update_density_bar_chart(fig_density, {})
                density_chart = ui.plotly(fig_density).classes("w-full")
            with ui.card().classes("w-full"):
                ui.label("Track ID vs Duration").classes("text-h6")
                fig_track_duration = go.Figure()
                update_track_duration_chart(fig_track_duration, [])
                track_duration_chart = ui.plotly(fig_track_duration).classes("w-full")

        # Right column: summary stats
        with ui.column().classes("w-80"):
            with ui.card().classes("w-full"):
                ui.label("Summary").classes("text-h6")
                total_label = ui.label("Total events: 0")
                entry_label = ui.label("Entries: 0")
                exit_label = ui.label("Exits: 0")
                density_label = ui.label("Density snapshots: 0")

    # Tables section
    with ui.row().classes("w-full p-4 gap-4"):
        with ui.column().classes("flex-1 min-w-0"):
            with ui.card().classes("w-full"):
                ui.label("All Events").classes("text-h6")
                events_table = ui.table(
                    columns=[
                        {"name": "event_type", "label": "Type", "field": "event_type", "align": "left"},
                        {"name": "zone", "label": "Zone", "field": "zone", "align": "left"},
                        {"name": "track_id", "label": "Track ID", "field": "track_id", "align": "left"},
                        {"name": "duration_s", "label": "Duration (s)", "field": "duration_s", "align": "left"},
                        {"name": "timestamp", "label": "Time", "field": "timestamp", "align": "left"},
                    ],
                    rows=[],
                    row_key="id",
                ).classes("w-full")

        with ui.column().classes("w-96"):
            with ui.card().classes("w-full"):
                ui.label("Dwell Time Summary (by zone)").classes("text-h6")
                dwell_table = ui.table(
                    columns=[
                        {"name": "zone", "label": "Zone", "field": "zone"},
                        {"name": "count", "label": "Sessions", "field": "count"},
                        {"name": "avg_duration_s", "label": "Avg (s)", "field": "avg_duration_s"},
                    ],
                    rows=[],
                ).classes("w-full")

    # Ask section - LLM analysis of CSV data
    with ui.card().classes("w-full m-4"):
        ui.label("Ask about your data").classes("text-h6")
        ui.label("Analyzes events from events.csv using pandas + LLM").classes("text-caption")
        with ui.row().classes("w-full gap-2"):
            question_input = ui.input(
                placeholder="e.g. Which was the busiest hour?",
                value="",
            ).classes("flex-1")
            ask_btn = ui.button("Ask")

        answer_label = ui.label("").classes("w-full mt-2 p-4 bg-gray-100 rounded text-wrap")

        def do_ask():
            q = (question_input.value or "").strip()
            if not q:
                ui.notify("Enter a question", type="warning")
                return
            ask_btn.set_enabled(False)
            answer_label.set_text("Thinking...")

            def run_in_thread():
                try:
                    answer = ask_events_llm(q)
                    answer_label.set_text(answer)
                except Exception as e:
                    answer_label.set_text(f"Error: {e}")
                finally:
                    ask_btn.set_enabled(True)

            threading.Thread(target=run_in_thread, daemon=True).start()

        ask_btn.on("click", do_ask)

    def events_content():
        events = fetch_events()
        if events is None:
            status.set_text("⚠ Webhook server offline (start webhook_server.py)")
            return
        status.set_text(f"✓ {len(events)} events")

        proc = process_events(events)
        total_label.set_text(f"Total events: {len(events)}")
        entry_label.set_text(f"Entries: {len(proc['entries'])}")
        exit_label.set_text(f"Exits: {len(proc['sessions'])}")
        density_label.set_text(f"Density snapshots: {len(proc['density_history'])}")

        update_occupancy_chart(fig_occupancy, proc["density_history"])
        occupancy_chart.update()
        update_density_bar_chart(fig_density, proc["latest_density"])
        density_chart.update()
        update_track_duration_chart(fig_track_duration, proc["track_durations"])
        track_duration_chart.update()

        events_table.rows = proc["all_events_table"][:100]  # limit to 100
        events_table.update()
        dwell_table.rows = proc["dwell_rows"]
        dwell_table.update()

    ui.timer(POLL_INTERVAL, events_content)
    events_content()


if __name__ in {"__main__", "__mp_main__"}:
    print("=" * 60)
    print("Retail Analytics Dashboard")
    print("=" * 60)
    print("Dashboard: http://localhost:8080")
    print("Start webhook_server.py first, then run dwell/density examples")
    print("=" * 60)
    ui.run(title="Retail Analytics Dashboard", port=8080, reload=False)
