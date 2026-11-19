#!/bin/bash
# Launch ArduPilot SITL instances in WSL2.
# Usage: ./start_sitl.sh [num_instances]
# Default: 1 instance. Pass 3 for multi-drone.

NUM=${1:-1}
ARDUPILOT_DIR="$HOME/ardupilot"
# Kingston, Ontario coordinates
LAT_BASE=44.225
LON_BASE=-76.495
ALT=90

if [ ! -d "$ARDUPILOT_DIR" ]; then
    echo "ERROR: ArduPilot not found at $ARDUPILOT_DIR"
    echo "Run: cd ~ && git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git"
    exit 1
fi

cd "$ARDUPILOT_DIR"

for i in $(seq 0 $((NUM - 1))); do
    PORT=$((14550 + i * 10))
    LAT=$(echo "$LAT_BASE + $i * 0.0001" | bc)
    LON=$LON_BASE

    echo "Starting SITL instance $i on port $PORT (lat=$LAT, lon=$LON)..."

    sim_vehicle.py \
        -v ArduCopter \
        --instance $i \
        -l "$LAT,$LON,$ALT,0" \
        --out="udp:$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):$PORT" \
        --no-rebuild \
        --no-mavproxy \
        -w &

    sleep 2
done

echo ""
echo "=========================================="
echo " $NUM SITL instance(s) running"
echo " Ports: $(for i in $(seq 0 $((NUM-1))); do echo -n "$((14550 + i*10)) "; done)"
echo " Connect from Windows: udp://:PORT"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all instances"
wait
