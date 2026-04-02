# Event Manager Integration Examples

Zone entry/exit and snapshot events emitted via EventManager (WebhookPlugin). Requires `degirum-event-management`, `flask`, `requests`.

## Run

```bash
# Terminal 1: Start webhook server
python webhook_server.py

# Terminal 2: Run emitter
python dwell_time_with_events_example.py   # Zone entry/exit events
python density_with_events_example.py      # Density snapshots every 5s

# Terminal 3: Dashboard (NiceGUI)
pip install nicegui plotly  # if not installed
python dashboard.py

# Terminal 4 (optional): Fetch events
python event_collector.py
```

## Dashboard

- **URL:** http://localhost:8080
- **Features:**
  - **Control Panel:** Start/stop analytics from UI (no need to run example scripts manually)
  - Configurable: video source, snapshot interval (Zone Density), min duration (Dwell Time)
  - Occupancy over time chart, current zone density bar chart
  - Events table (Type, Zone, Track ID, Duration, Time)
  - Dwell time summary by zone
  - **Ask:** Natural language questions about your data (e.g. "Which was the busiest hour?")
- **Dependencies:** `nicegui`, `plotly`, `requests`, `pyyaml` (see `requirements-dashboard.txt`)
- **Ask feature:** Webhook needs `pandas`, `openai`. Set `OPENAI_API_KEY` for LLM answers.

## Files

- `dwell_time_with_events_example.py` - Emits zone entry/exit events
- `density_with_events_example.py` - Emits density snapshots every N seconds
- `webhook_server.py` - Receives POST /events, GET /events, POST /ask, writes events.csv
- `event_collector.py` - Polls and fetches events
- `dashboard.py` - NiceGUI dashboard for events visualization
- `requirements-dashboard.txt` - Dashboard dependencies
