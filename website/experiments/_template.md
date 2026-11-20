---
# Copy this file to experiments/<your-slug>.md and fill it in.
# Files whose names start with "_" are not published.
# Run `python build.py` and open dist/index.html to check it.

title: Short, plain title of the experiment
# One of: proposal | percolating | published | graduated
#   proposal    - an idea we'd like to run; looking for owners or data
#   percolating - work in progress, early results
#   published   - results and code are public
#   graduated   - became part of an OHS project or pillar
stage: proposal
# Lower numbers show first within the same stage. Optional.
order: 10
# Make the card twice as wide. Use for one or two headline experiments.
featured: false

# One or two sentences. Shown on the card and at the top of the overlay.
summary: >
  What question this experiment answers, and the headline result if there is one.

# Big number on the card art. Optional: defaults to the stage name.
stat:
  value: "3x"
  label: what the number means

tags: [Tag one, Tag two]
authors: [First Last]
date: 2026-01-31          # optional, YYYY-MM-DD
byline: ""                # optional, overrides "authors · date"

# Card and overlay art. pattern: bars | dots | tiles.
# Or set image: to a path under assets/ (e.g. assets/my-exp/cover.png).
cover:
  from: "#07585C"
  to: "#4F3F83"
  pattern: tiles
  image: ""

# Optional video, shown at the top of the overlay:
# a YouTube or Vimeo link, or a path to an .mp4/.webm under assets/.
video: ""

# Buttons at the top of the overlay. The first with primary: true is filled.
links:
  - { label: Repo on GitHub, url: "https://github.com/ohs-foundation/ohs-labs", primary: true }
  - { label: Blog post, url: "https://ohs.foundation/blog" }

# Up to three headline numbers. Use {{kpis}} in the body to place them.
kpis:
  - { value: "42", label: what it measures }

# Charts you can place in the body with {{chart:<id>}}. Types:
#   grouped-bars - horizontal bars, one group per row label, one bar per series;
#                  several metrics get a toggle.
#   columns      - vertical bars per category, one per series; log: true for
#                  a log scale; line: draws a dashed reference line.
#   race         - animated race of the series for one group of a grouped-bars
#                  chart, by a time metric; ticks show a score metric.
charts:
  - id: my-chart
    type: columns
    categories:
      - { label: Before, sub: optional second line }
      - { label: After }
    series:
      - { name: Baseline, color: "#B7C2C4", values: [120, 100] }
      - { name: With OHS, color: "#07585C", values: [60, 30] }
    note: Where the numbers come from, with a [link](https://github.com/ohs-foundation/ohs-labs).
  # A grouped-bars example (several metrics get a toggle):
  # - id: results
  #   type: grouped-bars
  #   groups: [Model A, Model B]
  #   series:
  #     - { name: Without, color: "#B7C2C4" }
  #     - { name: With, color: "#07585C" }
  #   metrics:
  #     - { id: score, label: Score, format: "{v}/10", max: 10, highlight: 10, values: [[4, 10], [5, 10]] }
  #     - { id: cost, label: Cost, format: "${v2}", values: [[0.2, 0.5], [0.3, 0.6]] }

# Optional override for the "get involved" box at the end of the overlay.
involve:
  title: ""
  text: ""
---

{{kpis}}

## The question | What did we want to find out?

Why it matters, in two or three plain sentences. Link the issue or prior work
that started it.

## What we did | How we tested it

- The setup.
- What we measured and how.

## Results | The headline finding

{{chart:my-chart}}

## What we learned | Takeaways

- One finding per bullet.

## Get involved | How you can help

What a contributor could do next: rerun it, add a model, bring data.
