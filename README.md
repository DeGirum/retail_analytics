# retail_analytics

This directory contains working examples that demonstrate different retail analytics capabilities using 'degirum_retail' SDK.

## Installation

DeGirum hosts its own PyPI server for DeGirum packages.

```bash
pip install -i https://pkg.degirum.com degirum-retail
```

**Prerequisites:**

- **AI Hub Account:** Create an account at [DeGirum AI Hub](https://hub.degirum.com/) and set up a workspace. See [Workspace Plans](https://docs.degirum.com/ai-hub/workspace-plans) for details.
- **Authentication Token:** Set up your AI Hub token following the [token management guide](https://docs.degirum.com/pysdk/user-guide-pysdk/command-line-interface#manage-ai-hub-tokens).
- **Python & OS:** See [DeGirum PySDK Documentation](https://docs.degirum.com/pysdk/installation) for requirements.
- **Hardware Drivers (optional):** See [Runtimes & Drivers](https://docs.degirum.com/pysdk/runtimes-and-drivers) for hardware acceleration setup.

**Quick Start:** Use `@cloud` inference to try without installing drivers locally. The Quickstart example below uses local CPU models for immediate testing.

## Available Examples

### 1. Simple Retail Tracking
**File**: `retail_tracking_simple.py`
**Config**: `retail_config.yaml`

Basic retail tracking example with zone density analytics on a single zone.

```bash
python examples/retail_tracking_simple.py
```

### 2. Zone Density Analytics
**File**: `zone_density_example.py`
**Config**: `zone_density_config.yaml`

Monitors occupancy levels and capacity limits across multiple zones in real-time.

```bash
python examples/zone_density_example.py
```

### 3. Dwell Time Analytics
**File**: `dwell_time_example.py`
**Config**: `dwell_time_config.yaml`

Tracks how long people spend in zones and provides session analytics.

```bash
python examples/dwell_time_example.py
```

### 4. Zone Transition Analytics
**File**: `zone_transition_example.py`
**Config**: `zone_transition_config.yaml`

Tracks people moving between zones (e.g. left -> center -> right) and records transitions.

```bash
python examples/zone_transition_example.py
```

### 5. Gizmo Pipeline (Zone Density)
**File**: `gizmo_pipeline_example.py`
**Config**: `gizmo_pipeline_config.yaml`

Zone density analytics using the RetailTracker pipeline.

```bash
python examples/gizmo_pipeline_example.py
```

### 6. Simple Retail Analysis
**File**: `retail_analyzer_simple.py`
**Config**: `retail_analyzer_config.yaml`

Basic retail analytics example using RetailTracker pipeline to calculate zone density.

```bash
python examples/retail_analyzer_simple.py 
```

**Note:** Tracking examples (1–5) read the video source (file path, webcam index, or RTSP URL) from their YAML config via the `video_source` setting.

## Configuration Examples

### Zone Density Configuration
```yaml
analyzers:
  - type: "zone_density"
    zones: ["entrance_area", "waiting_zone", "service_area"]
    config:
      max_capacity:
        entrance_area: 5
        waiting_zone: 15
        service_area: 8
      show_annotations: true
      label_filter: ["person"]
```

### Dwell Time Configuration
```yaml
analyzers:
  - type: "dwell_time"
    zones: ["entrance", "waiting_area", "service_counter"]
    config:
      min_duration: 2.0
      show_annotations: true
      label_filter: ["person"]
```

### Zone Transition Configuration
```yaml
analyzers:
  - type: "zone_transition"
    zones: ["zone_left", "zone_center", "zone_right"]
    config:
      max_transition_time: 30.0
      min_duration: 1.0
      show_annotations: true
      label_filter: ["person"]
```

### Zone Definitions
```yaml
zones:
  entrance_area:
    - [100, 200]
    - [400, 200]
    - [400, 500]
    - [100, 500]
  waiting_zone:
    - [401, 200]
    - [800, 200]
    - [800, 500]
    - [401, 500]
```

## Getting Started

1. **Choose an example** based on your analytics needs
2. **Run from project root**:
   ```bash
   cd /path/to/retail_analytics
   python examples/zone_density_example.py
   ```
3. **Customize configuration** by editing the corresponding YAML file

## Requirements

- `degirum_retail` package installed
- `degirum_tools` package installed
- Webcam or video file available
- Internet connection for cloud models
