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
* Same ANC app spec given to coding agents cold vs with OHS Foundations (HAPI + kotlin-fhir + FHIR Engine + Data Capture) vs Foundations + agent skills
* Automated harness runs the grid across models (Haiku/Sonnet/Opus/Fable) with hermetic per-run state; results scored on cost, time, and verified-working
* Sweep 1 findings in [results/grid.md](ohs-agent-experiment/results/grid.md); skills for the three kotlin-fhir libraries in [skills/](ohs-agent-experiment/skills/)
