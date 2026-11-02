# OHS labs

Quick AI experiments that could become future Open Health Stack (OHS)
features or capabilities.

## Experiments

| Experiment | Status | Folder |
|---|---|---|
| Agentic coding evaluation on the OHS stack | Done, results published | [ohs-agent-experiment](ohs-agent-experiment/) |

### Agentic coding evaluation on the OHS stack

Measures what it costs an AI coding agent to build a standards-based
health app compared with a custom one. The agent builds the same
antenatal care app from a blank project (No FHIR), with the OHS
libraries and a FHIR server (OHS), and with the same plus [agent
skills](ohs-agent-experiment/skills/) for the libraries (OHS + skills).

With the three short skills, Gemini 3.8 Flash, Gemini 4 Argon, Claude
Sonnet, Opus and Fable each built a fully working FHIR app (10 out of 10
checks) for 50 cents more on average than a custom app. Without skills, the libraries
were the most expensive way to build.

Read the [blog post](ohs-agent-experiment/docs/blog-interoperability-tax.md)
for the results, or the [experiment README](ohs-agent-experiment/README.md)
to run it yourself.

## Ideas not started yet

- **Natural language querying of the OHS FHIR Data Pipes warehouse.**
  Skills that pull context from the FHIR Implementation Guide or
  configs, build the query and enforce guardrails (e.g. no DELETE), with
  MCP for the database layer, possibly packaged as a workflow.
- **Agentic workflow for deploying OHS FHIR Data Pipes.** A skill for
  working with FHIR Data Pipes, built on its existing APIs and
  documentation.
- **Skills for working with kotlin-fhir models.** A CLI wrapper around
  the kotlin-fhir models, skills defined from the API documentation, and
  a demo chat app working with FHIR data through the CLI.
