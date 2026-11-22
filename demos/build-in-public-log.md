# Build in Public — Drone Swarm C2

Daily content for LinkedIn + Twitter. Same post goes on both.

---

## Day 1 — First Flight (Nov 19)

**Hook:** Built a 3-drone swarm from scratch today.

**Post:**
Day 1 of building a natural language drone swarm command system.

Got 3 PX4 drones flying in formation in Gazebo simulation. They arm, take off to 20m, fly a triangle pattern with 30m spacing, hold for 10 seconds, and land.

Stack: PX4 v1.16 + Gazebo Harmonic + ROS2 Humble

The wild part: I started with ArduPilot, realized multi-drone SITL was too fragile, pivoted to PX4 mid-day, and had 3 drones flying by evening.

Also discovered PX4 writes flight logs that consumed 27GB in 7 hours and filled my disk. First bug of many.

Tomorrow: making them understand English.

#drones #robotics #buildinpublic #px4 #ros2

---

## Day 2 — Full E2E Pipeline (Nov 20)

**Hook:** Type English. Drones fly.

**Post:**
Day 2: I can now type "all 3 drones fly triangle formation at 20 meters" and they actually do it.

Full pipeline working:
→ Type a sentence
→ Claude (AI) parses the intent
→ Fleet manager allocates drones
→ Path planner computes waypoints
→ Drones fly in Gazebo

Also built a Command Center dashboard — web UI with live telemetry, drone cards, 2D map, and a command bar.

Bugs I fixed today:
- Magnetometer disabled → drones couldn't figure out which way is north → refused to arm
- Fleet manager excluded armed drones from missions (oops)
- Formation planner crashed when no center point given

The gap between "it parses correctly" and "drones actually move" was 4 bugs wide.

Tomorrow: camera feeds in the dashboard.

#drones #ai #buildinpublic #nlp #autonomy

---

## Day 3 — Camera Feed (Nov 21)

**Hook:** Now I can see what the drone sees.

**Post:**
Day 3: Live camera feed from the drone is now streaming into the Command Center dashboard.

Pipeline: Gazebo camera → ROS2 image bridge → JPEG encoder → MJPEG stream → browser

Click a drone card to switch cameras. Click the feed to expand.

Hit a wall though — 3 cameras made the simulation choppy. Rendering 3 viewpoints is brutal on CPU. For now, only drone 1 gets a camera. The real fix: moving the whole sim to an AWS GPU instance.

Also built a one-command cleanup script because PX4 keeps filling my disk. Third time this week.

The demo is coming together: type English → drones fly → see the camera feed. Next: voice input with Whisper so I can talk to the swarm.

#drones #computervision #buildinpublic #robotics #aws

---

## Template for future days

**Hook:** One punchy sentence. What happened today in 10 words or less.

**Post format:**
- Day N: [headline achievement]
- 2-3 sentences on what was built
- Technical detail that's interesting to non-experts
- One honest struggle/failure
- What's next tomorrow
- Hashtags: #drones #buildinpublic + 3-4 relevant ones
