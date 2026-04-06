#
# retail_events_example.py: Config-driven retail event generation
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Demonstrates RetailEventsApplication — all event triggers, thresholds, retail
# analyzers, and delivery (console + webhook) are defined in
# retail_events_config.yaml. No code changes are needed to add, remove, or
# reconfigure events.
#
# Run:
#   python retail_events_example.py                       # uses config video source
#   python retail_events_example.py /path/to/video.mp4
#   python retail_events_example.py 0                     # webcam index
#
# To receive webhook events, start the server in a separate terminal first:
#   python webhook_server.py
#

import sys
from pathlib import Path

import yaml

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from degirum_retail import RetailEventsApplication

CONFIG = Path(__file__).parent / "retail_events_config.yaml"


def main():
    with open(CONFIG) as f:
        settings = yaml.safe_load(f)

    # Allow video source to be overridden from the command line
    if len(sys.argv) >= 2:
        src = sys.argv[1]
        try:
            src = int(src)
        except ValueError:
            pass
        settings["stream"]["source"] = src

    app = RetailEventsApplication(settings=settings)

    # Optional: intercept every emission before connector delivery.
    # Return False from any handler to suppress delivery for that emission.
    @app.on_event
    def log(emission):
        print(
            f"[{emission.severity.upper()}] {emission.trigger_id}"
            f" | {emission.firing} | {emission.payload}"
        )

    print("Starting retail event pipeline — press Ctrl+C to stop.")
    app.run()


if __name__ == "__main__":
    main()
