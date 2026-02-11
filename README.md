# retail_analytics

This directory contains working examples that demonstrate different retail analytics capabilities using 'degirum_retail' SDK.

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

Batch analysis of images for person detection. Pass one or more image paths as arguments.

```bash
python examples/retail_analyzer_simple.py image1.jpg image2.jpg
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
