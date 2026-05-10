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
#   ./run.sh --export-map                           # export maps/rtabmap.db → map.pgm + map.yaml
#   ./run.sh --map jacaranda                        # use maps/jacaranda.db instead of rtabmap.db
#   ./run.sh --fresh-map                            # start a new map (backs up existing db)
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
EXPORT_MAP=false
MAP_NAME=""       # if set, uses maps/<name>.db; otherwise maps/rtabmap.db
FRESH_MAP=false   # if true, backs up existing db so the run starts fresh

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --svo)         USE_SVO=true ;;
    --loop)        SVO_LOOP=true ;;
    --localize)    LOCALIZE=true ;;
    --rebuild)     REBUILD=true ;;
    --shell)       OPEN_SHELL=true ;;
    --export-map)  EXPORT_MAP=true ;;
    --fresh-map)   FRESH_MAP=true ;;
    --cameras)     NUM_CAMERAS="$2"; _SVO_CAMERAS_OVERRIDE=true; shift ;;
    --svo-file)    SVO_FILE="$2";    shift ;;
    --map)         MAP_NAME="$2";    shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
  shift
done

# ── Resolve map database path ─────────────────────────────────────────────────
MAPS_DIR="$(dirname "$0")/maps"
if [[ -n "$MAP_NAME" ]]; then
  MAP_DB="$MAPS_DIR/${MAP_NAME}.db"
  MAP_DB_CONTAINER="/root/ros2_ws/maps/${MAP_NAME}.db"
else
  MAP_DB="$MAPS_DIR/rtabmap.db"
  MAP_DB_CONTAINER="/root/ros2_ws/maps/rtabmap.db"
fi

# ── --fresh-map: back up existing db so this run starts from scratch ──────────
if [[ "$FRESH_MAP" == true && -f "$MAP_DB" ]]; then
  BACKUP="${MAP_DB%.db}-backup-$(date +%Y%m%d-%H%M%S).db"
  echo "Backing up existing map to $(basename "$BACKUP")..."
  mv "$MAP_DB" "$BACKUP"
fi

# ── --export-map: convert the active map db → map.pgm + map.yaml ─────────────
if [[ "$EXPORT_MAP" == true ]]; then
  if [[ ! -f "$MAP_DB" ]]; then
    echo "Error: $(basename "$MAP_DB") not found. Run a SLAM session first."
    exit 1
  fi
  DB_BASENAME="$(basename "$MAP_DB")"
  PGM_NAME="${DB_BASENAME%.db}.pgm"
  YAML_NAME="${DB_BASENAME%.db}.yaml"
  echo ""
  echo "════════════════════════════════════════════════"
  echo "  Exporting 2-D occupancy grid from $DB_BASENAME..."
  echo "════════════════════════════════════════════════"
  docker-compose run --rm wheelchair_vision -c "
    source /opt/ros/jazzy/setup.bash
    cd /root/ros2_ws/maps
    rtabmap-reprocess -g2 $DB_BASENAME ./reprocess_tmp.db
    if [ -f ./reprocess_tmp_map.pgm ]; then
      mv ./reprocess_tmp_map.pgm ./$PGM_NAME
      rm -f ./reprocess_tmp.db
    fi
  "
  if [[ -f "$MAPS_DIR/$PGM_NAME" ]]; then
    cat > "$MAPS_DIR/$YAML_NAME" << MAPYAML
image: $PGM_NAME
resolution: 0.05
origin: [0.0, 0.0, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
MAPYAML
    PNG_NAME="${DB_BASENAME%.db}.png"
    if command -v convert &>/dev/null; then
      convert "$MAPS_DIR/$PGM_NAME" "$MAPS_DIR/$PNG_NAME"
      echo ""
      echo "Done. Map files written to maps/:"
      echo "  $PNG_NAME   — map image (open in Windows Explorer)"
      echo "  $PGM_NAME  — occupancy grid image"
      echo "  $YAML_NAME  — nav2 metadata"
    else
      echo ""
      echo "Done. Nav2 map files written to maps/:"
      echo "  $PGM_NAME  — occupancy grid image"
      echo "  $YAML_NAME  — nav2 metadata"
      echo "  (install imagemagick to also get a .png for easy viewing)"
    fi
  else
    echo ""
    echo "Warning: rtabmap-reprocess did not produce a .pgm file."
    echo "  The database may be too small (too few keyframes) to export a grid."
    echo "  Try running a longer recording first."
  fi
  exit 0
fi

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
LAUNCH_ARGS="$LAUNCH_ARGS rtabmap_db:=$MAP_DB_CONTAINER"

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
  echo "Active map database: $MAP_DB_CONTAINER"
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
  # SVO end causes ros2 launch to exit non-zero; disable set -e so the map
  # export step still runs after the pipeline stops.
  set +e
  docker-compose run --rm wheelchair_vision -c "$CONTAINER_CMD"
  set -e

  # ── Auto-export map after SVO replay ─────────────────────────────────────────
  if [[ "$USE_SVO" == true && "$SVO_LOOP" == false ]]; then
    if [[ -f "$MAP_DB" ]]; then
      DB_BASENAME="$(basename "$MAP_DB")"
      PGM_NAME="${DB_BASENAME%.db}.pgm"
      YAML_NAME="${DB_BASENAME%.db}.yaml"
      echo ""
      echo "════════════════════════════════════════════════"
      echo "  Exporting 2-D occupancy grid from $DB_BASENAME..."
      echo "════════════════════════════════════════════════"
      docker-compose run --rm wheelchair_vision -c "
        source /opt/ros/jazzy/setup.bash
        cd /root/ros2_ws/maps
        rtabmap-reprocess -g2 $DB_BASENAME ./reprocess_tmp.db
        if [ -f ./reprocess_tmp_map.pgm ]; then
          mv ./reprocess_tmp_map.pgm ./$PGM_NAME
          rm -f ./reprocess_tmp.db
        fi
      "
      if [[ -f "$MAPS_DIR/$PGM_NAME" ]]; then
        if [[ ! -f "$MAPS_DIR/$YAML_NAME" ]]; then
          cat > "$MAPS_DIR/$YAML_NAME" << MAPYAML
image: $PGM_NAME
resolution: 0.05
origin: [0.0, 0.0, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
MAPYAML
        fi
        PNG_NAME="${DB_BASENAME%.db}.png"
        if command -v convert &>/dev/null; then
          convert "$MAPS_DIR/$PGM_NAME" "$MAPS_DIR/$PNG_NAME"
          echo ""
          echo "Map saved to maps/  ($DB_BASENAME  $PNG_NAME  $PGM_NAME  $YAML_NAME)"
        else
          echo ""
          echo "Map saved to maps/  ($DB_BASENAME  $PGM_NAME  $YAML_NAME)"
        fi
      fi
    else
      echo ""
      echo "Warning: $(basename "$MAP_DB") was not written."
      echo "  RTAB-Map may have exited before processing any frames."
      echo "  Re-run with --shell to inspect logs interactively."
    fi
  fi
fi
