#!/usr/bin/env bash
set -euo pipefail

# Launch 3-drone PX4 SITL swarm with Gazebo + MicroXRCEAgent for ROS2.
# Usage: bash ~/drone-vla/scripts/start_px4_swarm.sh

PX4_DIR="$HOME/PX4-Autopilot"
NUM_DRONES=${1:-3}
# Use camera model: x500_mono_cam_45 (45-deg), x500_mono_cam (forward), x500 (no cam)
PX4_MODEL=${2:-gz_x500_mono_cam_45}
PIDS=()

cleanup() {
    echo ""
    echo "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    pkill -f MicroXRCEAgent 2>/dev/null || true
    wait 2>/dev/null || true
    echo "All processes stopped."
}
trap cleanup EXIT INT TERM

echo "=== Killing old processes ==="
pkill -f "px4.*-i [0-9]" 2>/dev/null || true
pkill -f "gz sim" 2>/dev/null || true
pkill -f MicroXRCEAgent 2>/dev/null || true
sleep 2

echo "=== Clearing old PX4 logs ==="
rm -rf "$PX4_DIR"/build/px4_sitl_default/rootfs/*/log/ \
       "$PX4_DIR"/build/px4_sitl_default/rootfs/log/ 2>/dev/null || true
rm -f /tmp/px4_drone*.log /tmp/px4_cam*.log /tmp/px4_swarm_startup.log /tmp/xrce_agent.log 2>/dev/null || true

cd "$PX4_DIR"

echo "=== Starting PX4 ${NUM_DRONES}-drone swarm ==="

echo "Starting drone 1 (starts Gazebo, model: ${PX4_MODEL})..."
PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL="${PX4_MODEL}" \
    ./build/px4_sitl_default/bin/px4 -i 1 > /dev/null 2>&1 &
PIDS+=($!)
echo "  PID: ${PIDS[-1]}"

echo "Waiting 20s for Gazebo + first drone..."
sleep 20

# Derive Gazebo model name from PX4_SIM_MODEL (strip gz_ prefix)
GZ_MODEL_BASE="${PX4_MODEL#gz_}"

for i in $(seq 2 "$NUM_DRONES"); do
    POSE_Y=$(( (i - 1) * 3 ))
    echo "Starting drone $i (pose: 0,${POSE_Y}, model: ${GZ_MODEL_BASE})..."

    GZ_WORLD=$(gz topic -l 2>/dev/null | grep -oP '/world/\K[^/]+' | head -1)
    GZ_WORLD=${GZ_WORLD:-default}

    gz service -s "/world/${GZ_WORLD}/create" \
        --reqtype gz.msgs.EntityFactory \
        --reptype gz.msgs.Boolean \
        --timeout 5000 \
        --req "sdf_filename: \"${GZ_MODEL_BASE}/model.sdf\", name: \"${GZ_MODEL_BASE}_${i}\", pose: {position: {y: ${POSE_Y}}}" \
        2>/dev/null || echo "  (model spawn via gz service failed, trying PX4 auto-spawn)"

    PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4001 \
        PX4_GZ_MODEL_NAME="${GZ_MODEL_BASE}_${i}" \
        ./build/px4_sitl_default/bin/px4 -i "$i" > /dev/null 2>&1 &
    PIDS+=($!)
    echo "  PID: ${PIDS[-1]}"
    sleep 8
done

echo ""
echo "=== Starting MicroXRCEAgent ==="
MicroXRCEAgent udp4 -p 8888 > /dev/null 2>&1 &
PIDS+=($!)
echo "  PID: ${PIDS[-1]}"
sleep 3

echo ""
echo "=== Setting params to disable preflight checks ==="
python3 "$HOME/drone-vla/scripts/set_px4_params.py" 2>&1 || true

echo ""
echo "=== Starting camera image bridges ==="
# Discover Gazebo world name and start ros_gz_image bridges for each drone camera
GZ_WORLD=$(gz topic -l 2>/dev/null | grep -oP '/world/\K[^/]+' | head -1)
GZ_WORLD=${GZ_WORLD:-default}
CAM_COUNT=0
for CAM_TOPIC in $(gz topic -l 2>/dev/null | grep "imager/image$"); do
    echo "  Bridge: $CAM_TOPIC"
    ros2 run ros_gz_image image_bridge "$CAM_TOPIC" > /dev/null 2>&1 &
    PIDS+=($!)
    CAM_COUNT=$((CAM_COUNT + 1))
done
if [ "$CAM_COUNT" -eq 0 ]; then
    echo "  No camera topics found (model may not have camera sensor)"
fi

echo ""
echo "=========================================="
echo " ${NUM_DRONES}-drone PX4 swarm running"
echo " Model: ${PX4_MODEL}"
echo ""
echo " ROS2 namespaces:"
for i in $(seq 1 "$NUM_DRONES"); do
    echo "   Drone $i: /px4_${i}/"
done
echo ""
echo " MicroXRCEAgent: UDP port 8888"
echo " Camera bridges: $CAM_COUNT"
echo " PX4 stdout: /dev/null (SDLOG_MODE=-1 disables .ulg too)"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all instances"
wait
