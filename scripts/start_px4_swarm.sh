#!/usr/bin/env bash
set -euo pipefail

# Launch 3-drone PX4 SITL swarm with Gazebo + MicroXRCEAgent for ROS2.
# Usage: bash ~/drone-vla/scripts/start_px4_swarm.sh

PX4_DIR="$HOME/PX4-Autopilot"
NUM_DRONES=${1:-3}
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

cd "$PX4_DIR"

echo "=== Starting PX4 ${NUM_DRONES}-drone swarm ==="

echo "Starting drone 1 (starts Gazebo)..."
PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500 \
    ./build/px4_sitl_default/bin/px4 -i 1 > /tmp/px4_drone1.log 2>&1 &
PIDS+=($!)
echo "  PID: ${PIDS[-1]}"

echo "Waiting 20s for Gazebo + first drone..."
sleep 20

for i in $(seq 2 "$NUM_DRONES"); do
    POSE_Y=$(( (i - 1) * 3 ))
    echo "Starting drone $i (pose: 0,${POSE_Y})..."

    # Spawn model via gz service
    GZ_WORLD=$(gz topic -l 2>/dev/null | grep -oP '/world/\K[^/]+' | head -1)
    GZ_WORLD=${GZ_WORLD:-default}

    gz service -s "/world/${GZ_WORLD}/create" \
        --reqtype gz.msgs.EntityFactory \
        --reptype gz.msgs.Boolean \
        --timeout 5000 \
        --req "sdf_filename: \"x500/model.sdf\", name: \"x500_${i}\", pose: {position: {y: ${POSE_Y}}}" \
        2>/dev/null || echo "  (model spawn via gz service failed, trying PX4 auto-spawn)"

    PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4001 \
        PX4_GZ_MODEL_NAME="x500_${i}" \
        ./build/px4_sitl_default/bin/px4 -i "$i" > "/tmp/px4_drone${i}.log" 2>&1 &
    PIDS+=($!)
    echo "  PID: ${PIDS[-1]}"
    sleep 8
done

echo ""
echo "=== Starting MicroXRCEAgent ==="
MicroXRCEAgent udp4 -p 8888 > /tmp/xrce_agent.log 2>&1 &
PIDS+=($!)
echo "  PID: ${PIDS[-1]}"
sleep 3

echo ""
echo "=== Setting params to disable preflight checks ==="
python3 "$HOME/drone-vla/scripts/set_px4_params.py" 2>&1 || true

echo ""
echo "=========================================="
echo " ${NUM_DRONES}-drone PX4 swarm running"
echo ""
echo " ROS2 namespaces:"
for i in $(seq 1 "$NUM_DRONES"); do
    echo "   Drone $i: /px4_${i}/"
done
echo ""
echo " MicroXRCEAgent: UDP port 8888"
echo " Logs: /tmp/px4_drone{1..${NUM_DRONES}}.log"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all instances"
wait
