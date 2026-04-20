# Wheelchair SLAM

Autonomous wheelchair localization and mapping stack built on **ROS 2 Jazzy**, **ZED Mini** stereo cameras, and **RTAB-Map**. Everything runs inside a Docker container — no host ROS installation needed.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker + Docker Compose | Any recent version |
| NVIDIA GPU | Required for ZED SDK / CUDA |
| [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) | Enables GPU access in containers |
| ZED Mini camera(s) | Up to 3 for live mode |
| X11 display server | Required to open RViz2 |

---

## Quick Start

```bash
chmod +x run.sh
./run.sh
```

The script will automatically build the Docker image on the first run (this takes a while — it installs ROS 2 Jazzy and the ZED SDK). Subsequent runs reuse the cached image.

---

## Usage

```bash
./run.sh [options]
```

| Option | Description |
|---|---|
| *(none)* | Live mode — 3 cameras, full SLAM |
| `--svo --svo-file <path>` | Replay mode — replay the given SVO file (required with `--svo`) |
| `--svo --svo-file <path> --loop` | Replay mode, looping the recording |
| `--cameras <n>` | Use `n` cameras in live mode (default: 3) |
| `--localize` | Localization only — load an existing map, do not build a new one |
| `--rebuild` | Force a full Docker image rebuild before launching |
| `--shell` | Open an interactive shell inside the container instead of launching SLAM |

### Examples

```bash
# Live SLAM with all 3 cameras
./run.sh

# Replay a saved SVO recording
./run.sh --svo --svo-file recordings/my-run.svo

# Replay on loop
./run.sh --svo --svo-file recordings/my-run.svo --loop

# Localization only (requires a map already saved in maps/)
./run.sh --localize

# Debug: open a shell inside the container
./run.sh --shell
```

---

## Project Layout

```
.
├── dockerfile              # Docker image definition (ZED SDK + ROS 2 Jazzy)
├── docker-compose.yml      # Container configuration (GPU, X11, volume mounts)
├── run.sh                  # One-command launcher
├── maps/                   # Saved RTAB-Map databases (.db files persist here)
├── recordings/             # SVO recordings for replay mode (see recordings/README.md)
└── src/
    └── wheelchair_slam/
        ├── launch/         # ROS 2 launch files
        │   ├── slam_full.launch.py       # Top-level entrypoint
        │   ├── zed_cameras.launch.py     # ZED camera nodes
        │   ├── pointcloud_merge.launch.py
        │   ├── odometry_fusion.launch.py # EKF sensor fusion
        │   ├── rtabmap.launch.py         # RTAB-Map SLAM / localization
        │   └── robot_description.launch.py
        └── config/
            ├── camera_params.yaml
            ├── ekf_params.yaml
            ├── rtabmap_params.yaml
            ├── scan_params.yaml
            └── zed_override.yaml
```

---

## Volumes

The container mounts three host directories so that data persists across runs:

| Host path | Container path | Purpose |
|---|---|---|
| `./recordings/` | `/root/ros2_ws/recordings/` | SVO files for replay |
| `./maps/` | `/root/ros2_ws/maps/` | RTAB-Map database output |
| `./src/` | `/root/ros2_ws/src/wheelchair_slam/` | Package source (live-reloaded) |

---

## Manual Launch (inside the container)

If you opened a shell with `./run.sh --shell`:

```bash
cd /root/ros2_ws
colcon build --packages-select wheelchair_slam --symlink-install
source install/setup.bash
ros2 launch wheelchair_slam slam_full.launch.py num_cameras:=3 use_svo:=false localization_only:=false
```
