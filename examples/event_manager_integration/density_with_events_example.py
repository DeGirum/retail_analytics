#
# density_with_events_example.py: Zone Density + EventManager Snapshot Example
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Emits density snapshots every N seconds via EventManager (WebhookPlugin).
# Collect with event_collector.py.
#

import sys
from pathlib import Path

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
from degirum_retail import ZoneDensityAnalyzer

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

    config_file = Path(__file__).resolve().parent.parent / "zone_density_config.yaml"
    config, _ = degirum_retail.RetailTrackingConfig.from_yaml(yaml_file=config_file)

    # Extract zone_density analyzer config
    density_cfg = None
    for a in config.analyzers:
        if a.get("type") == "zone_density":
            density_cfg = a
            break
    zone_ids = (density_cfg or {}).get("zones", list(config.zones.keys()))
    max_capacity = {}
    label_filter = {"person"}
    if density_cfg and density_cfg.get("config"):
        max_capacity = density_cfg["config"].get("max_capacity", {})
        lf = density_cfg["config"].get("label_filter")
        if lf:
            label_filter = set(lf) if isinstance(lf, (list, tuple)) else {lf}

    video_source = None
    if len(sys.argv) >= 2:
        video_source = sys.argv[1]
        try:
            video_source = int(video_source)
        except ValueError:
            pass
    source_path = video_source if video_source is not None else config.video_source
    # Resolve relative paths from config against examples/ directory
    if (
        video_source is None
        and isinstance(source_path, str)
        and source_path
        and not Path(source_path).is_absolute()
    ):
        source_path = str((config_file.parent / source_path).resolve())

    # Snapshot interval (seconds)
    snapshot_interval = 5.0
    if len(sys.argv) >= 3:
        try:
            snapshot_interval = float(sys.argv[2])
        except ValueError:
            pass

    # EventManager with WebhookPlugin
    webhook_url = "http://localhost:5000/events"
    plugin = create_webhook_plugin(source_id="retail_analytics", webhook_url=webhook_url)
    event_manager = EventManager(source_id="retail_analytics", transport_plugin=plugin)
    event_manager.start()

    # Callback: density snapshot every N seconds
    def on_density_snapshot(stats: dict, timestamp: float) -> None:
        event_manager.emit_event(
            event_type="retail.zone.density_snapshot",
            data={"stats": stats, "timestamp": timestamp},
            source_component_id="retail_analytics",
            broadcast=True,
        )
        summary = " | ".join(f"{z}: {s['current_occupancy']}/{s.get('max_capacity', '?')}" for z, s in stats.items())
        print(f"  [EMIT] retail.zone.density_snapshot | {summary}")

    # Define analyzer with snapshot callback
    analyzer = ZoneDensityAnalyzer(
        zone_ids=zone_ids,
        max_capacity=max_capacity,
        label_filter=label_filter,
        show_annotations=(density_cfg or {}).get("config", {}).get("show_annotations", True),
        snapshot_interval_seconds=snapshot_interval,
        snapshot_callback=on_density_snapshot,
    )

    # Build pipeline
    model = config.person_detection_model.load_model()
    model.output_class_set = list(label_filter)

    tracker = degirum_tools.ObjectTracker(
        track_thresh=config.tracker.get("track_thresh", 0.35),
        track_buffer=config.tracker.get("track_buffer", 30),
        match_thresh=config.tracker.get("match_thresh", 0.8),
        anchor_point=degirum_tools.AnchorPoint.CENTER,
        show_overlay=True,
        show_only_track_ids=False,
    )

    show_inzone = config.zone_counter.get("show_inzone_counters")
    if show_inzone not in ("time", "frames", "all", None):
        show_inzone = "time"

    zone_counter = degirum_tools.ZoneCounter(
        zones=config.zones,
        use_tracking=True,
        timeout_frames=config.zone_counter.get("timeout_frames", 3),
        enable_zone_events=True,
        triggering_position=degirum_tools.AnchorPoint.CENTER,
        show_inzone_counters=show_inzone,
    )

    pipeline = (
        VideoSourceGizmo(source_path)
        >> AiSimpleGizmo(model)
        >> AiAnalyzerGizmo([tracker, zone_counter, analyzer])
        >> VideoDisplayGizmo(window_titles="Density with Events", show_ai_overlay=True, show_fps=True)
    )
    composition = Composition(pipeline)

    print("=" * 60)
    print("Zone Density with Events (WebhookPlugin)")
    print("=" * 60)
    print("Webhook: http://localhost:5000/events (start webhook_server.py first)")
    print(f"Video: {source_path}")
    print(f"Snapshot interval: {snapshot_interval}s")
    print("Events: retail.zone.density_snapshot")
    print("Collect with: python event_collector.py")
    print("=" * 60)

    try:
        composition.start()
        composition.wait()
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        try:
            composition.stop()
        except Exception:
            pass  # Ignore if composition never started
        event_manager.stop()

    m = event_manager.get_metrics()
    if m:
        print(f"\nEvents processed: {m.get('events_processed', 0)}")
    print("Done")


if __name__ == "__main__":
    main()
