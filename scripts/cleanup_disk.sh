#!/usr/bin/env bash
set -euo pipefail

# Kill PX4/Gazebo/MicroXRCE processes and delete temp/log files to free disk.
# Usage: bash ~/drone-vla/scripts/cleanup_disk.sh

PX4_DIR="$HOME/PX4-Autopilot"

echo "=== Disk before cleanup ==="
df -h / | tail -1

echo ""
echo "=== Killing PX4/Gazebo/MicroXRCE ==="
pkill -f "px4.*-i [0-9]" 2>/dev/null && echo "  Killed PX4 instances" || echo "  No PX4 running"
pkill -f "gz sim" 2>/dev/null && echo "  Killed Gazebo" || echo "  No Gazebo running"
pkill -f MicroXRCEAgent 2>/dev/null && echo "  Killed MicroXRCEAgent" || echo "  No MicroXRCEAgent running"
sleep 2

echo ""
echo "=== Deleting PX4 stdout logs from /tmp ==="
for f in /tmp/px4_drone*.log /tmp/px4_cam*.log /tmp/px4_swarm_startup.log /tmp/xrce_agent.log; do
    if [ -f "$f" ]; then
        SIZE=$(du -sh "$f" 2>/dev/null | cut -f1)
        rm -f "$f"
        echo "  Deleted $f ($SIZE)"
    fi
done

echo ""
echo "=== Deleting PX4 .ulg flight logs ==="
ULG_COUNT=$(find "$PX4_DIR/build/px4_sitl_default/rootfs" -name "*.ulg" 2>/dev/null | wc -l)
if [ "$ULG_COUNT" -gt 0 ]; then
    ULG_SIZE=$(find "$PX4_DIR/build/px4_sitl_default/rootfs" -name "*.ulg" -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)
    find "$PX4_DIR/build/px4_sitl_default/rootfs" -name "*.ulg" -delete 2>/dev/null
    echo "  Deleted $ULG_COUNT .ulg files ($ULG_SIZE)"
else
    echo "  No .ulg files found"
fi
rm -rf "$PX4_DIR"/build/px4_sitl_default/rootfs/*/log/ \
       "$PX4_DIR"/build/px4_sitl_default/rootfs/log/ 2>/dev/null || true

echo ""
echo "=== Clearing Chrome cache ==="
if [ -d "$HOME/.cache/google-chrome/Default/Cache" ]; then
    CHROME_SIZE=$(du -sh "$HOME/.cache/google-chrome/Default/Cache" 2>/dev/null | cut -f1)
    rm -rf "$HOME/.cache/google-chrome/Default/Cache" "$HOME/.cache/google-chrome/Default/Code Cache" 2>/dev/null
    echo "  Cleared $CHROME_SIZE"
else
    echo "  No Chrome cache found"
fi

echo ""
echo "=== Disk after cleanup ==="
df -h / | tail -1
