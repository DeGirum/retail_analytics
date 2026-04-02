#
# dwell_time_with_events_example.py: Dwell Time + EventManager Example
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Simple example: define analyzer with callback, emit events via EventManager (WebhookPlugin).
#

import sys
from pathlib import Path
from dataclasses import asdict

# Project root (retail_analytics)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import degirum_tools
from degirum_tools.streams import (
    Composition,
    VideoSourceGizmo,
    AiSimpleGizmo,
    AiAnalyzerGizmo,
    VideoDisplayGizmo,
)

import degirum_retail
from degirum_retail import DwellTimeAnalyzer, SessionEvent, Session

try:
    from event_manager import EventManager
    from event_manager.plugin_registry import create_webhook_plugin
    EVENT_MANAGER_AVAILABLE = True
except ImportError:
    EVENT_MANAGER_AVAILABLE = False


def main():
    if not EVENT_MANAGER_AVAILABLE:
        print("ERROR: degirum-event-management not installed.")
        print("Install: pip install degirum-event-management")
        sys.exit(1)

    config_file = Path(__file__).resolve().parent.parent / "dwell_time_config.yaml"
    config, _ = degirum_retail.RetailTrackingConfig.from_yaml(yaml_file=config_file)

    video_source = None
    if len(sys.argv) >= 2:
        video_source = sys.argv[1]
        try:
            video_source = int(video_source)
        except ValueError:
            pass
    source_path = video_source if video_source is not None else config.video_source

    # EventManager with WebhookPlugin (POSTs to webhook server)
    webhook_url = "http://localhost:5000/events"
    plugin = create_webhook_plugin(source_id="retail_analytics", webhook_url=webhook_url)
    event_manager = EventManager(source_id="retail_analytics", transport_plugin=plugin)
    event_manager.start()

    # Callback: zone entry/exit -> emit via EventManager (broadcast=True to trigger webhook)
    def on_zone_event(event: SessionEvent, session: Session) -> None:
        event_type = f"retail.zone.{event.value}"
        event_manager.emit_event(
            event_type=event_type,
            data=asdict(session),
            source_component_id="retail_analytics",
            broadcast=True,
        )
        print(f"  [EMIT] {event_type} | zone={session.zone_id} track={session.track_id} duration={session.duration:.1f}s")

    # Define analyzer with callback (read from config)
    dwell_cfg = None
    for a in config.analyzers:
        if a.get("type") == "dwell_time":
            dwell_cfg = a
            break
    zone_ids = (dwell_cfg or {}).get("zones", list(config.zones.keys()))
    min_duration = 2.0
    if dwell_cfg and dwell_cfg.get("config"):
        min_duration = dwell_cfg["config"].get("min_duration", 2.0)
    analyzer = DwellTimeAnalyzer(
        zone_ids=zone_ids,
        min_duration=min_duration,
        label_filter={"person"},
        event_callback=on_zone_event,
    )

    # Build pipeline
    model = config.person_detection_model.load_model()
    model.output_class_set = ["person"]

    tracker = degirum_tools.ObjectTracker(
        track_thresh=config.tracker.get("track_thresh", 0.3),
        track_buffer=config.tracker.get("track_buffer", 30),
        match_thresh=config.tracker.get("match_thresh", 0.8),
        anchor_point=degirum_tools.AnchorPoint.CENTER,
        show_overlay=True,
        show_only_track_ids=False,
    )

    zone_counter = degirum_tools.ZoneCounter(
        zones=config.zones,
        use_tracking=True,
        timeout_frames=config.zone_counter.get("timeout_frames", 3),
        enable_zone_events=True,
        triggering_position=degirum_tools.AnchorPoint.CENTER,
        show_inzone_counters=config.zone_counter.get("show_inzone_counters", "time"),
    )

    pipeline = (
        VideoSourceGizmo(source_path)
        >> AiSimpleGizmo(model)
        >> AiAnalyzerGizmo([tracker, zone_counter, analyzer])
        >> VideoDisplayGizmo(window_titles="Dwell Time with Events", show_ai_overlay=True, show_fps=True)
    )
    composition = Composition(pipeline)

    print("=" * 60)
    print("Dwell Time with Events (WebhookPlugin)")
    print("=" * 60)
    print("Webhook: http://localhost:5000/events (start webhook_server.py first)")
    print(f"Video: {source_path}")
    print("Events: retail.zone.entered | retail.zone.session_complete")
    print("=" * 60)

    try:
        composition.start()
        composition.wait()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        composition.stop()
        event_manager.stop()

    m = event_manager.get_metrics()
    if m:
        print(f"\nEvents processed: {m.get('events_processed', 0)}")
    print("Done")


if __name__ == "__main__":
    main()
