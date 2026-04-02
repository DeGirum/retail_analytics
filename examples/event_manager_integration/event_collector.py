#
# event_collector.py: Fetch collected events from webhook server
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Run: python event_collector.py
# Fetches events from GET http://localhost:5000/events
# Start webhook_server.py first.
#

import time
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. pip install requests")
    sys.exit(1)

WEBHOOK_URL = "http://localhost:5000"
POLL_INTERVAL = 2.0


def fetch_events():
    """Fetch events from webhook server"""
    try:
        r = requests.get(f"{WEBHOOK_URL}/events", timeout=5)
        r.raise_for_status()
        return r.json().get("events", [])
    except requests.exceptions.ConnectionError:
        print("Cannot connect to webhook server. Is it running? (python webhook_server.py)")
        return None
    except Exception as e:
        print(f"Error fetching events: {e}")
        return None


def main():
    print("=" * 60)
    print("Event Collector - fetching from webhook server")
    print("=" * 60)
    print(f"Server: {WEBHOOK_URL}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    last_count = 0
    try:
        while True:
            events = fetch_events()
            if events is not None:
                if len(events) > last_count:
                    for evt in events[last_count:]:
                        etype = evt.get("event_type", "?")
                        data = evt.get("data", {})
                        if etype == "retail.zone.density_snapshot":
                            stats = data.get("stats", {})
                            summary = " | ".join(
                                f"{z}: {s.get('current_occupancy', 0)}/{s.get('max_capacity') or '?'}"
                                for z, s in stats.items()
                            )
                            print(f"  [FETCHED] {etype} | {summary}")
                        else:
                            print(f"  [FETCHED] {etype} | zone={data.get('zone_id')} track={data.get('track_id')} duration={data.get('duration', 0):.1f}s")
                    last_count = len(events)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped. Total events fetched:", last_count)


if __name__ == "__main__":
    main()
