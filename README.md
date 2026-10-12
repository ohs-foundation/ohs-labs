# OHS labs
Repository for defining quick AI experiments that could be rolled into future OHS features or capabilities

## Current explorations include:

### 1. Natural language querying of the OHS Data Pipes DWH using AI
* Build skill (or set of skills) for retrieving context from the FHIR Implementation Guide or configs, building the query and enforcing guardrails (e.g. can't DELETE) etc
* Leverage MCP for database layer execution
* Could package this up into a workflow

### 2. Agentic workflow for deploying OHS FHIR Data Pipes
* Develop skill for interacting with FHIR Data Pipes
* Can leverage existing APIs and documentation
* Demonstrate an agentic workflow

### 3. Skills for working with kotlin-fhir models
* Develop CLI wrapper to interact with the kotlin-fhir models
* Define skills from the API documentation to ensure validation etc
* Demonstrate agentic use case of a chat app working with FHIR data via the CLI

### 4. Agentic coding evaluation on the OHS stack ([ohs-agent-experiment](ohs-agent-experiment/))
Measures what it costs an AI agent to build a standards-based health app compared with a custom one. The agent gets the same antenatal care app spec three ways: a blank project (cold), the OHS libraries and a FHIR server (OHS), and the same plus [agent skills](ohs-agent-experiment/skills/) for the libraries.

Gemini 3.8 Flash via Antigravity CLI, average of two runs each:

| | Cold | OHS | OHS + skills |
|---|---|---|---|
| Cost | $0.84 | $3.48 | $1.46 |
| Time | 4.6 min | 16.4 min | 6.5 min |
| Data | JSON file on the phone | FHIR on a server | FHIR on a server |

* With skills, the standards-based app cost 62 cents more than the custom one.
* Without skills, the agent spent its time reverse-engineering the libraries.
* Claude models showed the same skills effect ([results/grid.md](ohs-agent-experiment/results/grid.md)).
* One task, two runs each: the direction is clear, the exact size is not.
