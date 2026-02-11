#
# zone_density_example.py: Zone Density Analytics Example
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Demonstrates zone density analytics by tracking occupancy levels and capacity
# limits across multiple zones in real-time using DeGirum Retail SDK.
#
# You can configure all the settings in the `zone_density_config.yaml` file.
#

import sys
from pathlib import Path

# Add project root to path for local development
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import degirum_retail


def main():
    # Load settings from YAML file
    config_file = Path(__file__).parent / "zone_density_config.yaml"
    config, _ = degirum_retail.RetailTrackingConfig.from_yaml(yaml_file=config_file)

    # Use command-line video source if provided, otherwise fall back to config
    video_source = None
    if len(sys.argv) >= 2:
        video_source = sys.argv[1]
        # Try to convert to int if it's a camera index
        try:
            video_source = int(video_source)
        except ValueError:
            pass  # Keep as string for file paths or RTSP URLs

    print("=" * 60)
    print("Zone Density Analytics Example")
    print("=" * 60)
    print(f"Video source: {video_source or config.video_source}")
    print(f"Zones: {list(config.zones.keys())}")
    print(f"Analyzers: {[a['type'] for a in config.analyzers]}")
    print("Press 'q' in the display window or Ctrl+C to stop")
    print("=" * 60)

    # Create RetailTracker instance
    tracker = degirum_retail.RetailTracker(config)

    # Start tracking pipeline
    composition = tracker.start_tracking_pipeline(
        video_source=video_source,
        window_title="Zone Density Analytics"
    )

    try:
        # Start and wait for completion
        composition.start()
        composition.wait()
    except KeyboardInterrupt:
        print("\nStopping pipeline...")
    finally:
        tracker.stop()

    print("Pipeline completed")


if __name__ == "__main__":
    main()
