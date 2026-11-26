# Build in Public — Drone Swarm C2

Daily content for LinkedIn + Twitter. Same post goes on both.

---

## Day 1 — First Flight (Nov 19)

**Hook:** Built a 3-drone swarm from scratch today.

**Post:**
Day 1 of building a natural language drone swarm command system.

Started the morning on ArduPilot, realized multi-drone SITL was too fragile, pivoted to PX4 mid-day, and had 3 drones flying triangle formation in Gazebo by evening. Arm, take off to 20m, hold 30m spacing, land.

Stack: PX4 v1.16 + Gazebo Harmonic + ROS2 Humble

Then PX4 silently wrote 27GB of flight logs in 7 hours and filled my disk. First bug of many.

Tomorrow: making them understand English.

#drones #robotics #buildinpublic #px4 #ros2

---

## Day 2 — Full E2E Pipeline (Nov 20)

**Hook:** Type English. Drones fly.

**Post:**
Day 2: I can now type "all 3 drones fly triangle formation at 20 meters" and they actually do it.

Full pipeline: type a sentence → Claude parses intent → fleet manager allocates drones → path planner computes waypoints → drones fly in Gazebo.

Also built a Command Center — web dashboard with live telemetry, drone cards, 2D map, and a command bar.

The gap between "it parses correctly" and "drones actually move" was 4 bugs wide. Magnetometer disabled so drones couldn't find north, fleet manager excluding armed drones, formation planner crashing with no center point. The real work isn't the AI or the drones — it's the glue between them.

Tomorrow: camera feeds in the dashboard.

#drones #ai #buildinpublic #nlp #autonomy

---

## Day 3 — Camera Feed (Nov 21)

**Hook:** Now I can see what the drone sees.

**Post:**
Day 3: Live camera feed streaming into the Command Center dashboard.

Pipeline: Gazebo camera → ROS2 image bridge → JPEG encoder → MJPEG stream → browser. Click a drone card to switch cameras, click the feed to expand.

Hit a wall though — 3 cameras made the sim choppy. Rendering 3 viewpoints is brutal on CPU, so only drone 1 gets a camera for now. The real fix: moving the whole sim to an AWS GPU instance.

Also built a cleanup script because PX4 filled my disk again. Third time this week.

The demo is coming together: type English → drones fly → see the camera feed. Next: voice input with Whisper so I can talk to the swarm.

#drones #computervision #buildinpublic #robotics #aws

---

## Day 4-5 — SAR Village (Nov 24-25)

**Hook:** I built a search and rescue village and taught my drones to sweep it.

**Post:**
Day 4-5: Custom SAR village — buildings, roads, vehicles, simulated survivors — all built in code, no 3D modeling needed. Dropped 3 drones into it.

Biggest upgrade: the AI remembers context now. "Search for survivors" → "make it 50m radius" → "send drone 2 to help" — it tracks the whole conversation instead of starting from zero each time.

Thought the camera was mounted backward — spent an hour in the 3D model files before realizing the drone just wasn't rotating to face its direction of travel. One line of trig and it works perfectly.

Other wins: per-drone commands ("drone 1 land" no longer lands all 3), clean lawnmower search patterns, and a hover command.

Best bug: collision avoidance sending 30 warnings/sec to the browser and crashing Chrome. The safety system was the most dangerous thing in the sim.

Next: YOLO + Claude Vision so the drone actually spots things instead of just flying over them.

**Screenshots to capture:**
- Command Center with SAR village map + 3 drones flying
- Camera feed showing the village from drone POV
- Chat log showing a multi-turn conversation
- Gazebo view of the village with drone models

#drones #ai #searchandrescue #buildinpublic #autonomy #computervision

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
