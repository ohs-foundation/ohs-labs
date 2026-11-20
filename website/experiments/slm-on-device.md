---
title: FHIR via small language models on device
stage: percolating
order: 1
summary: >
  Can a small model on a phone read a patient's FHIR record? Turning FHIR JSON
  into SQL-on-FHIR views and Markdown (Tokempic) makes the record about 12
  times smaller.
stat: { value: "~12×", label: fewer tokens per patient record }
tags: [Gemma 4 E2B, LiteRT-LM, SQL-on-FHIR, KMP]
byline: Experiment 1 · emulator results
cover: { from: "#0B6F8A", to: "#07858A", pattern: dots }
links:
  - { label: fhir-slm-on-device on GitHub, url: "https://github.com/ohs-foundation/ohs-labs/tree/main/fhir-slm-on-device", primary: true }
  - { label: Tokempic, url: "https://github.com/recodelabs/tokempic" }
kpis:
  - { value: "~12×", label: "smaller than raw FHIR JSON: about 42 tokens per resource against about 541" }
  - { value: "51 s", label: "to answer over 10 visits with Tokempic. One visit of raw JSON took 9.4 minutes" }
  - { value: "10–20", label: "visits fit on an 8 GB phone with Tokempic" }
charts:
  - id: tokens
    type: columns
    log: true
    categories:
      - { label: 1 visit, sub: 47 FHIR resources }
      - { label: 10 visits, sub: 166 FHIR resources }
      - { label: 51 visits, sub: 703 FHIR resources }
    series:
      - { name: Raw FHIR JSON, color: "#B7C2C4", values: [25486, 90741, 380033] }
      - { name: Tokempic, color: "#0C87A7", values: [2116, 7108, 29857] }
    line: { value: 4096, label: "4,096-token context", legend: "Gemma 4 E2B default context (4,096 tokens)", color: "#4F3F83" }
    note: >
      Log scale. Emulator on CPU; times will be faster on a real phone, token
      counts are the same on any device. Memory grows with context: about
      2.2 GB at 4K, 2.8 GB at 8K, 3.9 GB at 16K and 6.0 GB at 32K. Source:
      [fhir-slm-on-device](https://github.com/ohs-foundation/ohs-labs/tree/main/fhir-slm-on-device).
---

{{kpis}}

## The question | Can a phone-sized model read a patient's record?

Health workers often have no reliable connection. A small language model
running on the phone could summarise a patient's history offline, but raw FHIR
JSON is huge. This experiment tests whether converting FHIR to SQL-on-FHIR
views and Markdown with [Tokempic](https://github.com/recodelabs/tokempic)
makes the record small enough to fit. It comes from the OHS issue
"Exploration: FHIR via LLMs on device".

## What we did | Gemma 4 E2B on Android, one synthetic patient

- **slm-runtime:** a Kotlin Multiplatform library that runs a model on device through LiteRT-LM and measures each run.
- **slm-bench:** an Android app on top of it. Type a prompt, or start a measured run from adb.
- **Experiment 1:** grow the record from 1 to 51 visits and compare prompt tokens, time and memory for raw JSON and Tokempic.

## Results | Prompt tokens as the record grows

{{chart:tokens}}

## What's next | Real phones and real questions

Experiment 1 covers size and speed. Results so far are from an emulator. Help
us run it on real devices with at least 8 GB of RAM, and test answer quality on
clinical questions.
