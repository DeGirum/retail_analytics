#
# minimal_events_example.py: Dwell Time + EventManager snapshot demo
#
# Uses RetailTracker (config-driven) like dwell_time_example.py.
# Events (EventManager, snapshot callback) are in code since config doesn't support them.
#

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import degirum_retail

try:
    from event_manager import EventManager
    from event_manager.plugin_registry import create_webhook_plugin
except ImportError:
    print("ERROR: pip install degirum-event-management")
    sys.exit(1)


def main():
    config_file = Path(__file__).resolve().parent.parent / "dwell_time_config.yaml"
    config, _ = degirum_retail.RetailTrackingConfig.from_yaml(yaml_file=config_file)

    video_source = None
    if len(sys.argv) >= 2:
        video_source = sys.argv[1]
        try:
            video_source = int(video_source)
        except ValueError:
            pass

    # EventManager (events in code - config doesn't support callbacks)
    plugin = create_webhook_plugin(source_id="retail_analytics", webhook_url="http://localhost:5000/events")
    event_manager = EventManager(source_id="retail_analytics", transport_plugin=plugin)
    event_manager.start()

    def on_dwell_snapshot(stats: dict, active_sessions: dict, timestamp: float) -> None:
        event_manager.emit_event(
            event_type="retail.zone.dwell_snapshot",
            data={"stats": stats, "active_sessions": active_sessions, "timestamp": timestamp},
            source_component_id="retail_analytics",
            broadcast=True,
        )
        summary = " | ".join(f"{z}: {s.get('people_count', 0)} active" for z, s in stats.items())
        print(f"  [EMIT] retail.zone.dwell_snapshot | {summary}")

    tracker = degirum_retail.RetailTracker(config)
    composition = tracker.start_tracking_pipeline(
        video_source=video_source,
        window_title="Dwell Time + Events",
        snapshot_callback=on_dwell_snapshot,
    )

    print("Dwell Time + EventManager | Webhook: localhost:5000/events | Snapshots every 5s (from config)")
    try:
        composition.start()
        composition.wait()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        tracker.stop()
        event_manager.stop()
    print("Done")


if __name__ == "__main__":
    main()
