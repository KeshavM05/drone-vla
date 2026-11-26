# Build in Public — Drone Swarm C2

Daily content for LinkedIn + Twitter. Same post goes on both.

---

## Day 1 — First Flight (Nov 19)

**Hook:** I mass pivoted frameworks mid-day and still got 3 drones flying by evening.

**Post:**
Day 1 of building a natural language drone swarm command system.

I started the morning on ArduPilot. By lunch I realized multi-drone simulation was too fragile to build on — random crashes, flaky connections, hours wasted debugging someone else's bugs. So I scrapped it and switched to PX4.

By evening, 3 drones were flying triangle formation in Gazebo. Arm, takeoff to 20m, hold 30m spacing, land. Clean.

Then my disk filled up. PX4 writes flight logs silently in the background — 27GB in 7 hours from 3 idle drones. I didn't notice until builds started failing with "no space left on device." First lesson: always kill your sim when you're done.

Stack: PX4 v1.16 + Gazebo Harmonic + ROS2 Humble. Tomorrow I'm wiring up Claude so I can talk to these things in English.

#drones #robotics #buildinpublic #px4 #ros2

---

## Day 2 — Full E2E Pipeline (Nov 20)

**Hook:** Type English. Drones fly.

**Post:**
Day 2: I typed "all 3 drones fly triangle formation at 20 meters" and watched them actually do it.

The pipeline is deceptively simple — type a sentence, Claude parses the intent into structured JSON, the fleet manager picks which drones go where, the path planner computes waypoints, and PX4 flies them. Five systems talking to each other, end to end.

Building it was not simple. The drones refused to arm because I'd disabled the magnetometer in simulation — turns out they still need to know which way is north even in a fake world. Then the fleet manager kept saying "no drones available" because it was filtering out armed drones. Then the formation planner crashed because I forgot to handle "no center point."

Four bugs between "the AI understands me" and "the drones move." That's the real work — not the AI, not the drones, but the glue.

Also built a Command Center dashboard with live telemetry, 2D map, and a command bar. Feels like a real ground station now.

Tomorrow: camera feeds so I can see what the drone sees.

#drones #ai #buildinpublic #nlp #autonomy

---

## Day 3 — Camera Feed (Nov 21)

**Hook:** Now I can see what the drone sees.

**Post:**
Day 3: The drone has eyes now.

I piped the Gazebo camera through ROS2, encoded frames to JPEG, and streamed them as MJPEG into the Command Center. Click a drone card, see its camera. Click the feed, it goes fullscreen.

Then I tried giving all 3 drones cameras and the simulation dropped to a slideshow. Rendering 3 viewpoints on a laptop CPU is brutal. So for now, drone 1 is the scout with the camera and drones 2-3 are wingmen. The real fix is moving the sim to a GPU instance on AWS — I have $25K in credits waiting.

Also wrote a one-command cleanup script because PX4 filled my disk again. Third time this week. At this point it's a daily ritual.

But step back and look at what's working: I type English, drones fly, and I watch through their camera. That's a command-and-control system. Next I'm adding Whisper so I can just talk to them.

#drones #computervision #buildinpublic #robotics #aws

---

## Day 4-5 — SAR Village (Nov 24-25)

**Hook:** I built a search and rescue village and taught my drones to sweep it.

**Post:**
Day 4-5: I built an entire SAR village in code — buildings, roads, vehicles, shipping containers, colored ground markers as simulated survivors — and dropped 3 drones into it.

The breakthrough was giving the AI memory. Before, every command started from zero: "search for survivors" → "Please provide GPS coordinates." Now it remembers context. I can say "search for survivors," then "make it a 50m radius instead," then "send drone 2 to help" and it tracks the whole conversation. Feels like talking to a copilot instead of filling out forms.

I spent an hour thinking the camera was mounted backward. The drone was flying forward but showing what's behind it. Dug into the 3D model files, almost rewired the camera orientation — then realized the drone just wasn't rotating to face its direction of travel. One line of trig (atan2 toward the next waypoint) and the camera works perfectly.

The funniest bug: my collision avoidance system was sending 30 safety warnings per second to the browser and crashing Chrome. The safety system was the most dangerous thing in the sim.

Also: per-drone commands actually work now ("drone 1 land" no longer lands all 3), clean lawnmower search sweeps, and a hover/loiter command for holding position.

Next up: teaching the drone to actually see. YOLO for real-time object detection + Claude Vision for scene understanding. Right now it flies over things. Soon it'll spot them.

**Screenshots to capture:**
- Command Center with SAR village map + 3 drones flying
- Camera feed showing the village from drone POV (buildings visible)
- Chat log showing a multi-turn conversation (search → refine → execute)
- Gazebo view of the village with drone models visible

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
