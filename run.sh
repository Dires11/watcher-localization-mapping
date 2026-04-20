#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# run.sh  —  One-command launcher for the wheelchair SLAM pipeline.
#
# Usage:
#   ./run.sh                                        # 3 live cameras, full SLAM
#   ./run.sh --svo --svo-file recordings/my.svo     # replay an SVO recording
#   ./run.sh --svo --svo-file recordings/my.svo --loop  # loop the recording
#   ./run.sh --cameras 1                            # use only 1 camera (live)
#   ./run.sh --localize                             # localization-only (no new mapping)
#   ./run.sh --rebuild                              # force Docker image rebuild first
#   ./run.sh --shell                                # open a bash shell instead of launching SLAM
# ──────────────────────────────────────────────────────────────────────────────
set -e

# ── Defaults ────────────────────────────────────────────────────────────────
NUM_CAMERAS=3
USE_SVO=false
_SVO_CAMERAS_OVERRIDE=false   # tracks whether --cameras was set explicitly
SVO_FILE=""
SVO_LOOP=false
LOCALIZE=false
REBUILD=false
OPEN_SHELL=false

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --svo)        USE_SVO=true ;;
    --loop)       SVO_LOOP=true ;;
    --localize)   LOCALIZE=true ;;
    --rebuild)    REBUILD=true ;;
    --shell)      OPEN_SHELL=true ;;
    --cameras)    NUM_CAMERAS="$2"; _SVO_CAMERAS_OVERRIDE=true; shift ;;
    --svo-file)   SVO_FILE="$2";    shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
  shift
done

# Validate SVO mode
if [[ "$USE_SVO" == true && -z "$SVO_FILE" ]]; then
  echo "Error: --svo requires --svo-file <path>"
  echo "  Example: ./run.sh --svo --svo-file recordings/my-run.svo"
  exit 1
fi

# SVO mode with a single file → default to 1 camera unless overridden
if [[ "$USE_SVO" == true && "$_SVO_CAMERAS_OVERRIDE" == false ]]; then
  NUM_CAMERAS=1
fi

# ── Ensure host directories exist ────────────────────────────────────────────
mkdir -p "$(dirname "$0")/maps"
mkdir -p "$(dirname "$0")/src"

# ── X11 forwarding (needed for RViz2) ────────────────────────────────────────
if command -v xhost &>/dev/null; then
  xhost +local:docker &>/dev/null || true
fi

# ── Build Docker image if needed ─────────────────────────────────────────────
IMAGE_NAME="zed-jazzy-latest"

if [[ "$REBUILD" == true ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
  echo ""
  echo "════════════════════════════════════════════════"
  echo "  Building Docker image (this takes a while)..."
  echo "════════════════════════════════════════════════"
  docker-compose build
fi

# ── Build the ROS2 command to run inside the container ───────────────────────
LAUNCH_ARGS="num_cameras:=$NUM_CAMERAS"
LAUNCH_ARGS="$LAUNCH_ARGS use_svo:=$USE_SVO"
LAUNCH_ARGS="$LAUNCH_ARGS svo_file:=$SVO_FILE"
LAUNCH_ARGS="$LAUNCH_ARGS svo_loop:=$SVO_LOOP"
LAUNCH_ARGS="$LAUNCH_ARGS localization_only:=$LOCALIZE"

CONTAINER_CMD=$(cat <<'EOF'
set -e
cd /root/ros2_ws
source /opt/ros/jazzy/setup.bash

echo ""
echo "════════════════════════════════════════════════"
echo "  Building wheelchair_slam package..."
echo "════════════════════════════════════════════════"
colcon build \
  --packages-select wheelchair_slam \
  --symlink-install \
  --cmake-args=-DCMAKE_BUILD_TYPE=Release \
  --event-handlers console_cohesion+

source install/setup.bash
echo ""
echo "════════════════════════════════════════════════"
echo "  Launching SLAM pipeline..."
echo "════════════════════════════════════════════════"
echo ""
EOF
)

if [[ "$OPEN_SHELL" == true ]]; then
  echo ""
  echo "Opening shell inside the container..."
  echo "To launch manually:"
  echo "  cd /root/ros2_ws"
  echo "  colcon build --packages-select wheelchair_slam --symlink-install"
  echo "  source install/setup.bash"
  echo "  ros2 launch wheelchair_slam slam_full.launch.py $LAUNCH_ARGS"
  echo ""
  # ENTRYPOINT is /bin/bash — pass no command so it drops into an interactive shell
  docker-compose run --rm wheelchair_vision
else
  CONTAINER_CMD="$CONTAINER_CMD
ros2 launch wheelchair_slam slam_full.launch.py $LAUNCH_ARGS"
  # ENTRYPOINT is /bin/bash — pass -c "..." directly, no redundant 'bash' prefix
  docker-compose run --rm wheelchair_vision -c "$CONTAINER_CMD"
fi
