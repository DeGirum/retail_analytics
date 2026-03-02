#
# retail_analyzer_simple.py: Simple Retail Image Analysis Example
#
# Copyright DeGirum Corporation 2025
# All rights reserved
#
# Implements a simple retail image analysis example using DeGirum Retail SDK.
# This example demonstrates how to analyze individual images for person detection.
#
# You can configure all the settings in the `retail_analyzer_config.yaml` file.
#

import sys
import os
from pathlib import Path

# Add project root to path for local development
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import degirum_retail


def main():
    # Check if any image paths were provided
    if len(sys.argv) < 2:
        print(f"Usage: python {os.path.basename(__file__)} <image_path1> [image_path2] [image_path3] ...")
        sys.exit(1)

    # Load settings from YAML file
    config_file = Path(__file__).parent / "retail_analyzer_config.yaml"
    config, _ = degirum_retail.RetailAnalyticsConfig.from_yaml(yaml_file=config_file)

    # Create RetailAnalyzer instance
    analyzer = degirum_retail.RetailAnalyzer(config)

    print("=" * 60)
    print("Simple Retail Image Analysis Example")
    print("=" * 60)

    # Analyze images iterating over command line arguments
    for result in analyzer.predict_batch(iter(sys.argv[1:])):
        image_info = getattr(result, 'info', 'Unknown image')
        print(f"\nResults for {image_info}:")
        print(f"  Detected {len(result.results)} person(s)")
        
        for i, detection in enumerate(result.results):
            bbox = detection.get('bbox', [0, 0, 0, 0])
            score = detection.get('score', 0.0)
            print(f"    Person {i+1}: bbox={bbox}, confidence={score:.2f}")


if __name__ == "__main__":
    main()