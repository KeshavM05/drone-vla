---
title: Cost and Long-Term Feasibility Analysis
description: "Full financial breakdown from 8-week MVP through 12-month scaling: hardware, cloud, regulatory, revenue model, and funding path"
tags:
  - plan
  - cost
  - feasibility
  - business
  - scaling
---
# Cost and Long-Term Feasibility Analysis

Parent: [Master Plan](./master-plan.md)

This document covers every dollar from the 8-week MVP build through a 12-month path to first paying customer. Numbers are realistic ranges, not best-case fantasies.

---

## 1. Total Project Cost: 8-Week MVP

### Hardware: 3x DIY ArduPilot Builds

Chosen platform: SpeedyBee F405 V4 stack on 5" frames. See [Hardware Recommendations](./hardware-recommendations.md).

| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| SpeedyBee F405 V4 FC+ESC stack | 3 | $55 | $165 |
| 5" frame (Source One clone / Mark4) | 3 | $20 | $60 |
| 2306 2450KV motors (set of 4) | 3 | $35 | $105 |
| BN-880 GPS + compass | 3 | $14 | $42 |
| 5045 tri-blade props (2 sets) | 3 | $8 | $24 |
| 4S 1300-1550mAh LiPo | 3 | $22 | $66 |
| **Drone subtotal** | | | **$462** |

| Shared Equipment | Cost |
|-----------------|------|
| LiPo charger (ISDT Q6 or similar) | $35 |
| XT60 pigtails, wires, connectors | $10 |
| Spare props (3 extra sets) | $12 |
| Battery voltage checker/alarm (3x) | $8 |
| ESP32 modules for Wi-Fi telemetry (3x) | $18 |
| Soldering iron + solder (if you lack one) | $25 |
| Heat shrink, zip ties, mounting tape | $8 |
| **Shared subtotal** | **$116** |

| **Total hardware** | **$578** |
|---------------------|----------|

### AWS Usage (from $20K credits)

All estimates assume the 8-week dev period.

| Service | Usage Estimate | Unit Price | 8-Week Cost |
|---------|---------------|------------|-------------|
| **Bedrock (Claude Sonnet)** | ~2,000 commands parsed (dev + testing) | ~$0.006/command (avg 500 input + 800 output tokens) | ~$12 |
| **Bedrock (Claude Sonnet)** prompt iteration | ~500 longer prompt-tuning calls | ~$0.015/call | ~$8 |
| **EC2 g5.xlarge** (YOLOv8 training) | ~10 hours | $1.006/hr | ~$10 |
| **EC2 c5.2xlarge** (remote SITL if needed) | ~40 hours | $0.34/hr | ~$14 |
| **S3** (telemetry logs, model weights) | ~5 GB | $0.023/GB/mo | ~$0.25 |
| **CloudWatch** (logging) | minimal | | ~$1 |
| **Total AWS** | | | **~$45** |

You will use roughly **$45 of your $20,000 credits** during the MVP. The credits are overwhelmingly a scaling asset, not an MVP one.

### Software and Tools

| Tool | Cost |
|------|------|
| ArduPilot firmware | Free (open source, GPLv3) |
| MAVSDK-Python | Free (open source, BSD-3) |
| ROS2 Humble | Free (open source, Apache 2.0) |
| Gazebo | Free (open source, Apache 2.0) |
| faster-whisper | Free (open source, MIT) |
| YOLOv8 (Ultralytics) | Free for research (AGPL-3.0; commercial license $750/yr if selling product) |
| Python, Docker, Git | Free |
| OBS Studio (screen recording) | Free |
| **Total software** | **$0 during MVP** |

Note: YOLOv8's AGPL license means if you ship a product containing it, you either open-source your code or buy the Ultralytics commercial license ($750/yr). Not relevant during MVP/demo phase, but relevant before first customer.

### Operating and Hidden Costs

| Item | Cost | Notes |
|------|------|-------|
| Extra LiPo batteries (3x spare) | $66 | You will want 2 batteries per drone for field testing |
| Replacement props (crashes happen) | $20 | Budget 5 sets total |
| Replacement frame arm (1-2 crashes) | $15 | 5" arms are cheap |
| Travel to outdoor test site | $0-40 | Depends on location; park may be free |
| LiPo safety bag | $10 | Non-negotiable for charging safety |
| Portable Wi-Fi router (5GHz) | $25 | Dedicated network for drone comms |
| SD card (for logging) | $10 | If logging onboard |
| **Operating subtotal** | **$146-186** |

### 8-Week MVP Total

| Category | Cost |
|----------|------|
| Drone hardware | $578 |
| AWS (from credits) | $45 |
| Software | $0 |
| Operating/hidden | $166 (midpoint) |
| **Grand total out-of-pocket** | **~$744** |
| **Of which AWS credits cover** | **-$45** |
| **Actual cash needed** | **~$700** |

This is $100 over the stated $600 budget. The overage comes from spare batteries and the Wi-Fi router. You can defer spare batteries to week 5 (when physical testing starts) and use an existing router to stay within $600 for weeks 1-4.

---

## 2. Ongoing Monthly Costs (Post-Demo Development)

### AWS Bedrock Command Parsing

Claude Sonnet on Bedrock pricing (as of late 2026): ~$3/M input tokens, ~$15/M output tokens.

Average command parse: ~500 input tokens, ~800 output tokens = ~$0.0135/command.

| Scale | Commands/Day | Monthly Cost | Notes |
|-------|-------------|-------------|-------|
| Solo dev | 10 | ~$4 | You testing |
| Demo/pilot | 100 | ~$41 | Single customer trial |
| Small deployment | 1,000 | ~$405 | 5-10 operators |
| Production | 10,000 | ~$4,050 | 50+ operators |

At production scale, you would switch to a smaller fine-tuned model or prompt caching to cut this 5-10x.

### Hardware Maintenance

| Item | Frequency | Monthly Cost |
|------|-----------|-------------|
| LiPo replacement | Every 200-300 cycles (~6-12 months) | ~$11 (amortized) |
| Props | Every 20-30 flights | ~$8 |
| Motor bearings | Every 6 months | ~$5 (amortized) |
| Frame repairs (occasional crash) | As needed | ~$5 |
| **Monthly hardware maintenance** | | **~$29/month** for 3 drones |

### Connectivity

| Item | Monthly Cost |
|------|-------------|
| AWS misc (S3, CloudWatch, EC2 dev) | ~$20 |
| Cellular data plan for field ops (optional) | $30-50 |
| **Monthly connectivity** | **$50-70** |

### Total Monthly Burn (Post-Demo, Solo Dev)

| Category | Monthly |
|----------|--------|
| AWS Bedrock (dev scale) | ~$4 |
| AWS infra | ~$20 |
| Hardware maintenance | ~$29 |
| Connectivity | ~$30 |
| **Total** | **~$83/month** |

With $19,955 in remaining AWS credits, the cloud portion is covered for **years** at dev scale.

---

## 3. Scaling Cost Analysis

### Hardware Scaling

| Fleet Size | Per-Drone Cost | Total Hardware | Why Cost Changes |
|------------|---------------|----------------|------------------|
| 3 (demo) | ~$155 | ~$465 | DIY, SpeedyBee F405 |
| 10 (team demo) | ~$155 | ~$1,550 | Same build, bulk prop/battery savings |
| 50 (customer pilot) | ~$300-500 | $15,000-25,000 | Upgrade to Pixhawk for reliability; add companion computer |
| 500 (production) | ~$800-1,500 | $400K-750K | Custom PCB, Pixhawk-class FC, onboard Jetson, redundant comms, weatherproofing |

### Compute Scaling

| Fleet Size | Monthly Cloud | Notes |
|------------|--------------|-------|
| 3 | ~$24 | Solo dev |
| 10 | ~$80 | More telemetry ingestion, more commands |
| 50 | ~$500-1,000 | Dedicated inference endpoint, telemetry DB |
| 500 | ~$5,000-15,000 | Multi-region, real-time streaming, model serving fleet |

### Communication Infrastructure

| Fleet Size | Comms Approach | Monthly Cost |
|------------|---------------|-------------|
| 3 | Wi-Fi (5GHz router) | $0 (one-time $25) |
| 10 | Wi-Fi mesh + 4G backup | ~$100 |
| 50 | Dedicated LTE/5G + mesh radios | ~$1,500-3,000 |
| 500 | Private LTE or satellite (Starlink) | ~$10,000-30,000 |

### Regulatory Costs

| Fleet Size | Regulatory Need | Cost |
|------------|----------------|------|
| 3 (demo) | Basic RPAS pilot cert (Canada) or Part 107 (US) | $150-400 one-time |
| 10 | SFOC (Canada) or Part 107 waiver for swarm ops | $500-2,000 + legal |
| 50 | BVLOS waiver, operational approval | $5,000-20,000 + ongoing compliance |
| 500 | Type certification path, insurance, SOC2 | $50,000-200,000/yr |

### Total Scaling Summary

| Fleet Size | Year 1 Total Cost | Key Unlock |
|------------|-------------------|------------|
| 3 | ~$1,700 | Demo video, pitch |
| 10 | ~$5,000-8,000 | Investor demo, team validation |
| 50 | ~$80,000-150,000 | First paying customer pilot |
| 500 | ~$1M-2.5M | Production deployment |

---

## 4. Revenue Model Feasibility

### The Blueprint's Claim: $1,000-5,000/drone/month

This is aggressive but not unreasonable for enterprise/government contracts. Here is the reality check.

### What the Customer Actually Pays For

| Layer | You Provide | Alternative | Your Defensibility |
|-------|------------|-------------|--------------------|
| Hardware | Nothing (they own drones) | They already have drones | N/A |
| Flight control | ArduPilot (open source) | Free, anyone can use it | Low |
| **NL command interface** | Your intent parser + orchestrator | Nobody else has this | **High** |
| **Swarm coordination** | Your fleet manager + path planner | Manual waypoint planning | **High** |
| **Autonomous failover** | Your mission executor | Manual reprogramming | **High** |
| Edge detection | YOLOv8 integration | They can DIY this | Medium |

Your moat is the **NL-to-swarm translation layer** and the **autonomous orchestration**. The customer is paying to turn 1 operator + 50 drones from impossible to effortless.

### Realistic Pricing Tiers

| Tier | Target Customer | Price/Drone/Month | Fleet Size | Monthly Revenue |
|------|----------------|-------------------|------------|----------------|
| Starter | SAR teams, small PDs | $500 | 5-10 | $2,500-5,000 |
| Professional | Fire departments, ports | $1,000 | 10-50 | $10,000-50,000 |
| Enterprise | Military, border security | $2,000-5,000 | 50-500 | $100K-2.5M |

### Unit Economics (Professional Tier)

| Metric | Value |
|--------|-------|
| Revenue per drone/month | $1,000 |
| Cloud cost per drone/month | ~$10-20 (at scale with caching) |
| Support allocation per drone/month | ~$50 |
| Gross margin per drone | **~$930 (93%)** |
| Customer fleet size (avg) | 20 drones |
| Revenue per customer/month | $20,000 |
| Revenue per customer/year | $240,000 |

### Break-Even Analysis

| Phase | Monthly Burn | Revenue Needed | Customers Needed (at $20K/mo avg) |
|-------|-------------|---------------|-----------------------------------|
| Solo founder (post-demo) | ~$3,000 (personal + infra) | $3,000 | 1 small contract |
| Small team (3 people) | ~$25,000 | $25,000 | 2 professional contracts |
| Series A team (10 people) | ~$150,000 | $150,000 | 8 professional contracts |

The margins are real because the incremental cost of adding a drone to the platform is nearly zero. The hard cost is acquiring each customer (long sales cycles in government/enterprise).

---

## 5. Funding Path

### What the Demo Unlocks

A video of 3 physical drones responding to natural language voice commands is a **top-1% YC application artifact**. Most drone startups show slides; you show atoms moving.

| Opportunity | Typical Check | What They Want to See |
|-------------|--------------|----------------------|
| YC | $500K (standard deal) | Working demo, founder-market fit, large market |
| Speedrun (a]6z) | $500K-1M | Technical depth, speed of execution |
| Founders Inc | $250K-500K | Unique insight, defensible tech |
| Angel investors | $25K-100K each | Passion, domain expertise, demo |
| Pre-seed round | $1M-3M total | All of the above + early design partners |

### Typical Pre-Seed for Robotics/Drone Startups

- **Range:** $1M-3M
- **Valuation:** $5M-15M pre-money
- **Timeline:** 3-6 months post-demo to close
- **Use of funds:** 12-18 months of runway (team of 3-5)

### How Far Seed Funding Goes

Assume $2M raised at $10M pre-money valuation:

| Expense | Monthly | 18-Month Total |
|---------|---------|---------------|
| 3 founders (modest salary) | $30,000 | $540,000 |
| 2 engineers | $25,000 | $450,000 |
| Cloud infrastructure | $2,000 | $36,000 |
| Drone fleet (30 units for pilots) | one-time | $15,000 |
| Office / coworking | $2,000 | $36,000 |
| Legal, insurance, regulatory | $3,000 | $54,000 |
| Travel (customer sites) | $3,000 | $54,000 |
| Buffer | | $315,000 |
| **Total** | | **$1,500,000** |
| **Runway** | | **~18 months** |

### Milestones Investors Want to See

1. **Demo day (you are here):** Working prototype, 3 drones, voice control
2. **Letter of intent:** One SAR team or fire department says "we would pay for this"
3. **Paid pilot:** One customer running your software on their fleet (even $1K/month)
4. **Repeatability:** Second customer acquired without custom engineering
5. **Retention:** First customer renews or expands

---

## 6. Technical Risk Assessment

### What Could Go Wrong (and Cost Money)

| Risk | Probability | Financial Impact | Mitigation |
|------|------------|-----------------|------------|
| Drone crash during demo filming | High (30-40%) | $50-150 per crash (parts) | Spare parts, practice runs, safety pilot |
| SpeedyBee FC reliability issue | Medium (15%) | $55 replacement + time | Test extensively in sim first; have 1 spare FC |
| GPS accuracy insufficient for tight formations | Medium (20%) | Time cost (tuning) | Use RTK GPS at scale ($100+/unit); demo with wider spacing |
| LLM hallucinated dangerous command | Low (5%) | Crash or unsafe behavior | Safety bounds in executor; never trust raw LLM output for altitude/speed |
| AWS Bedrock latency spike during demo | Low (10%) | Embarrassing demo failure | Cache common commands; have fallback responses |
| ArduPilot firmware bug with SpeedyBee | Low (10%) | Days of debugging | Use stable release; test specific firmware version |

### Regulatory Risks

**Canada (Transport Canada):**
- Basic RPAS pilot certificate: required for any outdoor drone flight
- Advanced certificate: required for flights in controlled airspace or near people
- SFOC (Special Flight Operations Certificate): required for swarm operations, BVLOS
- Timeline: Basic cert can be done in 1-2 days; SFOC takes 4-12 weeks

**United States (FAA):**
- Part 107: required for commercial operations
- Part 107 waiver: needed for swarm/multi-drone operations, night ops, BVLOS
- Timeline: Part 107 exam in 1-2 weeks; waivers take 3-6 months

**For the demo:** Fly in uncontrolled airspace, below 400ft AGL, visual line of sight, with a basic pilot cert. This is the legal path for the 8-week timeline.

### Insurance

| Phase | Coverage Needed | Annual Cost |
|-------|----------------|------------|
| Demo / dev | Hobby liability (if available) or self-insure | $0-200/yr |
| Customer pilot | Commercial drone liability ($1M) | $1,200-3,000/yr |
| Production | Product liability + E&O + commercial drone | $5,000-15,000/yr |

### Competition

| Competitor | Threat Level | Their Advantage | Your Advantage |
|-----------|-------------|----------------|----------------|
| **Degla Inc** (YC F26) | High | YC network, Boston talent, funded | You ship faster; they are also early |
| **Swarmer/STYX** (Austin) | High | 100K+ combat missions, revenue, IPO path | They sell to military; you can target SAR/commercial first |
| **Shield AI** | Low (different tier) | $2.7B raised, V-BAT platform | They build full aircraft; you are software-only |
| **FlytBase** | Medium | Existing drone fleet mgmt platform | They lack NL interface; you can integrate on top |
| **DJI FlightHub 2** | Medium | Massive install base | Proprietary, DJI-only; you are hardware-agnostic |

Your window: NL-to-swarm is a new category. Degla is the most direct competitor. Speed and demo quality are the differentiators right now.

---

## 7. 12-Month Roadmap Cost Projection

From demo (Jan 2027) to first paying customer.

| Month | Phase | Cash Out | AWS Credits Used | Cumulative Cash | Key Event |
|-------|-------|----------|-----------------|----------------|------------|
| Month 0 (Jan) | Demo complete | $0 | $0 | $700 | Demo video live |
| Month 1 (Feb) | Apply to YC/accelerators | $200 | $20 | $900 | Applications submitted |
| Month 2 (Mar) | Interviews + iterate | $200 | $30 | $1,100 | YC interview (if accepted) |
| Month 3 (Apr) | Accelerator starts OR self-fund | $500 | $50 | $1,600 | First design partner intro |
| Month 4 (May) | Build customer-facing features | $500 | $100 | $2,100 | Web dashboard, logging |
| Month 5 (Jun) | First customer pilot prep | $1,000 | $200 | $3,100 | 10-drone fleet built |
| Month 6 (Jul) | Customer pilot live | $1,500 | $300 | $4,600 | Real ops with SAR team |
| Month 7 (Aug) | Iterate on pilot feedback | $500 | $200 | $5,100 | Feature requests addressed |
| Month 8 (Sep) | Pilot converts to paid | $300 | $200 | $5,400 | **First revenue ($2K-5K/mo)** |
| Month 9 (Oct) | Second customer outreach | $500 | $300 | $5,900 | Pipeline building |
| Month 10 (Nov) | Fundraise (pre-seed) | $1,000 | $200 | $6,900 | Deck + metrics + demo |
| Month 11 (Dec) | Close round | $500 | $100 | $7,400 | Term sheet signed |
| Month 12 (Jan 28) | Money in bank | $0 | $0 | $7,400 | **$1-3M raised** |
| | | | | | |
| **Totals** | | **~$6,700 cash** | **~$1,700 credits** | | $18,300 credits remaining |

### Summary

| Metric | Value |
|--------|-------|
| Cash needed to reach first revenue | ~$5,400 |
| AWS credits needed to reach first revenue | ~$1,200 |
| Time to first revenue | ~8 months post-demo |
| Cash needed to reach fundraise | ~$7,400 |
| Remaining AWS credits at fundraise | ~$18,300 |

The $20K AWS credits last well past fundraising. The real constraint is the ~$7,400 in cash across the year, which includes scaling from 3 to 10 drones for the customer pilot. If you get into YC ($500K), the cash constraint evaporates at month 3.

---

## Bottom Line

| Question | Answer |
|----------|--------|
| Can you build the MVP for under $700? | Yes, with the SpeedyBee DIY builds |
| Can you reach demo day on $20K AWS credits? | You will use less than $50 of them |
| Is the SaaS revenue model real? | Yes: 93% gross margin at $1K/drone/month |
| What is the biggest financial risk? | The 8-month gap between demo and first revenue |
| What kills the project financially? | Not getting into an accelerator AND running out of personal runway |
| What is the best-case path? | YC acceptance (Feb/Mar) removes all cash constraints |