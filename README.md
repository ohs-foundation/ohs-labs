# OHS Labs

AI experiments that could become future Open Health Stack (OHS)
features or capabilities.

## Experiments

| Experiment | Status | Repo |
|---|---|---|
| Agentic coding evaluation on the OHS stack | Done, results published | [labs-ohs-agent](https://github.com/ohs-foundation/labs-ohs-agent) |

### [Agentic coding evaluation on the OHS stack](https://github.com/ohs-foundation/labs-ohs-agent)

Measures what it costs an AI coding agent to build a standards-based
health app compared with a custom one. The agent builds the same
antenatal care app from a blank project (No FHIR), with the OHS
libraries and a FHIR server (OHS), and with the same plus [agent
skills](https://github.com/ohs-foundation/labs-ohs-agent/tree/main/skills) for the libraries (OHS + skills).

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
