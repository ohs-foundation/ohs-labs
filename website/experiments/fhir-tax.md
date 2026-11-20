---
title: The "FHIR Tax" is shrinking
stage: published
order: 1
featured: true
summary: >
  We had AI coding agents build the same offline-first antenatal care app four
  ways. With the OHS libraries and Agent Skills, five models built a fully
  working FHIR app for about 50 cents more than a custom one.
stat: { value: "10/10", label: working apps with OHS + Skills }
tags: [Agentic coding, Agent Skills, Kotlin FHIR, Android]
authors: [Fikri Milano, Jing Tang]
date: 2026-11-05
cover: { from: "#07585C", to: "#4F3F83", pattern: bars }
video: ""
links:
  - { label: Read the blog post, url: "https://ohs.foundation/blog/fhir-standards-tax", primary: true }
  - { label: labs-ohs-agent on GitHub, url: "https://github.com/ohs-foundation/labs-ohs-agent" }
  - { label: The Agent Skills, url: "https://github.com/ohs-foundation/labs-ohs-agent/tree/main/skills" }
  - { label: Every app's score, url: "https://github.com/ohs-foundation/labs-ohs-agent/blob/main/results/app-scores.md" }
kpis:
  - { value: "10/10", label: "score for 5 of 6 models with OHS + Skills, against 4/10 for the custom app" }
  - { value: "+$0.50", label: "average extra cost per build for a fully working FHIR app, at API prices" }
  - { value: "46 runs", label: "reproducible for about $69 and 6 hours of agent time" }
charts:
  - id: results
    type: grouped-bars
    groups: [Claude Sonnet 5.5, Gemini 4 Argon, Claude Opus 5.5, Gemini 3.8 Flash, Claude Fable 5.1]
    series:
      - { name: No FHIR, color: "#B7C2C4" }
      - { name: FHIR without OHS, color: "#0C87A7" }
      - { name: OHS libraries, color: "#7262B7" }
      - { name: OHS + Skills, color: "#07585C" }
    metrics:
      - id: score
        label: App score
        format: "{v}/10"
        max: 10
        highlight: 10
        values: [[4,6,6,10],[4,6,8,10],[4,6,8,10],[4,5,8,10],[4,6,8,10]]
      - id: cost
        label: Cost per build
        format: "${v2}"
        max: 8
        values: [[0.24,0.72,0.78,0.54],[0.63,0.44,4.05,0.80],[0.70,1.08,2.65,1.17],[0.84,1.08,3.48,1.22],[1.53,2.56,7.48,2.73]]
      - id: min
        label: Minutes per build
        format: "{v1} min"
        max: 25
        values: [[1.5,6.0,5.9,3.2],[8.7,6.3,23.3,8.9],[4.1,4.7,7.8,4.7],[4.6,15.6,16.4,13.5],[3.9,9.6,17.8,5.2]]
    note: >
      Averages of the runs per condition, at API prices. Haiku never built a
      FHIR app that works offline, even with skills, so it is left out. Source:
      [labs-ohs-agent results](https://github.com/ohs-foundation/labs-ohs-agent#results).
  - id: replay
    type: race
    from: results
    group: Claude Opus 5.5
    time: min
    extra: cost
    ticks: score
    note: Claude Opus 5.5, scaled to build time. Each tick is one of the 10 checks the app passed.
---

{{kpis}}

## The question | Does FHIR still cost developers extra when an agent writes the code?

Digital health projects have long skipped FHIR because it took more time and
effort. [Health Samurai showed](https://www.health-samurai.io/articles/fhir-as-a-framework-for-agentic-coding),
from impressions, that agents build more coherent apps on a FHIR stack. We
tested that claim on the OHS stack with measurements.

## What we did | Same app spec, four starting points

An agent got the same spec for an offline-first Android antenatal care (ANC)
register and built it under one of four conditions. A working app lists
patients, shows visit history, records new visits, keeps data after a restart
and syncs both ways with a FHIR server.

- **No FHIR:** a blank Android project. The agent picks its own data model and storage.
- **FHIR without OHS:** the same project plus a local HAPI FHIR server and seed data. Any library allowed.
- **OHS libraries:** Kotlin FHIR Models, FHIR Engine and Data Capture, plus the FHIR server.
- **OHS + Skills:** the same OHS setup, plus agent skills written for the libraries.

Each condition ran twice on Claude Haiku, Sonnet, Opus and Fable (Claude Code)
and Gemini 3.8 Flash and Gemini 4 Argon (Antigravity CLI), at medium effort.
Every run got a fresh session, folder, server and device. A person installed
every app and scored it on 10 checks.

## Results | Skills turn the most expensive setup into the best one

{{chart:results}}

## Run replay | Watch one model build the app four ways

{{chart:replay}}

## What we learned | Takeaways

- Without FHIR, every model built an app that looked fine and scored 4/10: no server, no sync.
- The OHS libraries alone raised scores to 6 to 8, but agents spent the most time and money learning the APIs.
- Agent Skills for the libraries fixed that: five models reached 10/10, faster and cheaper than with the libraries alone.
- The "FHIR tax" for agent-built apps is now about 50 cents a build.
