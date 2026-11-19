#!/usr/bin/env bash
set -euo pipefail

# Launch 3-drone Gazebo swarm with ArduPilot SITL instances.
# Usage: ./start_gazebo_swarm.sh
# Ctrl+C to stop everything.

export GZ_SIM_SYSTEM_PLUGIN_PATH="$HOME/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
export GZ_SIM_RESOURCE_PATH="$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH:-}"
export PATH="$PATH:$HOME/ardupilot/Tools/autotest"

PIDS=()

cleanup() {
    echo ""
    echo "Shutting down..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    echo "All processes stopped."
}
trap cleanup EXIT INT TERM

echo "=== Starting Gazebo with 3-drone swarm world ==="
gz sim -v4 -r iris_swarm.sdf &
PIDS+=($!)
echo "Gazebo PID: ${PIDS[-1]}"

echo "Waiting 15s for Gazebo to initialize..."
sleep 15

echo "=== Starting 3 SITL instances ==="
for i in 0 1 2; do
    PORT=$((14550 + i * 10))
    echo "Starting SITL instance $i (MAVLink out: UDP $PORT)..."
    sim_vehicle.py \
        -v ArduCopter \
        -f gazebo-iris \
        --model JSON \
        -I "$i" \
        --no-rebuild \
        --no-mavproxy \
        --out="udp:127.0.0.1:$PORT" &
    PIDS+=($!)
    sleep 5
done

echo ""
echo "=========================================="
echo " 3-drone swarm running"
echo " MAVSDK ports: 14550, 14560, 14570"
echo " Gazebo world: iris_swarm.sdf"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all instances"
wait
