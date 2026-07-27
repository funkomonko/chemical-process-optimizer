# Chemical Process Optimization via Agentic Workflows

## Overview
This project is an autonomous, AI-driven multi-agent system designed to procedurally generate, debug, and optimize chemical process flowsheets in **DWSIM**. By bridging large language models (LLMs) with legacy .NET chemical simulation software, the system can autonomously write simulation code, diagnose its own execution and topological errors, and apply numerical methods to achieve specific thermodynamic targets without human intervention.

## Core Technologies
* **Framework:** LangGraph (Stateful Multi-Agent Orchestration)
* **LLM Engine:** Groq API (`gpt-oss-120b`)
* **Simulation Engine:** DWSIM (Open-Source Process Simulator)
* **Interop Layer:** Python.NET (`pythonnet`)
* **Optimization Algorithm:** Secant Method

## System Architecture

The system utilizes a directed graph architecture ("Swarm") consisting of three primary agents and an execution node:

1. **The Architect Agent:** 
   Generates the Python.NET code required to interact with the DWSIM automation API. It respects strict topological rules (e.g., managing intermediate material streams between unit operations) and initializes the thermodynamic property packages, feed states, and unit operations.
   
2. **The System Node (Executor):** 
   Executes the Architect's code directly within the DWSIM environment. If the code compiles and runs successfully, it extracts the thermodynamic data. If it fails, it captures the raw C#/.NET traceback and passes it to the Debugger.

3. **The Debugger Agent:** 
   Analyzes stack traces and execution failures. It translates cryptic .NET API errors (e.g., `ArgumentOutOfRangeException`, invalid port indices, or illegal direct unit-to-unit connections) into actionable natural language feedback, routing back to the Architect for iterative correction.

4. **The Optimizer Agent:** 
   Once the flowsheet compiles successfully, this agent takes over. It uses numerical optimization—specifically the **Secant Method**—to iteratively adjust independent variables (like a Heater's temperature) to hit a precise dependent target (such as a 0.5 vapor fraction in a downstream flash drum).

## Key Technical Features

* **Self-Healing Execution Loop:** The swarm can autonomously recover from API hallucinations, incorrect port mappings, and invalid thermodynamic topologies by iterating between the Architect and Debugger until the flowsheet compiles.
* **Sliding Window Memory:** Implemented aggressive context management that truncates conversational history to the last two execution errors, preventing token overflow while maintaining the agent's short-term problem-solving memory.
* **API Rate Limit Orchestration:** Features a built-in throttling mechanism (30-second delays per node execution) to strictly adhere to the Groq API's 8,000 Tokens Per Minute (TPM) constraint during rapid-fire LLM iterations.
* **Advanced DWSIM Topology Handling:** Programmatically enforces DWSIM's strict topological rules, such as using intermediate streams for unit-to-unit connections and leveraging `-1, -1` auto-resolve port indices for robust graph building.

## Example Use Case: Flash Separation Optimization
In a standard run, the system is tasked with separating a 50/50 molar mixture of Water and Ethanol using the Peng-Robinson property package. 
1. The **Architect** builds the flowsheet: Feed Stream -> Heater -> Intermediate Stream -> Flash Vessel -> Vapor/Liquid Products.
2. The **Debugger** ensures the connections are geometrically valid within the DWSIM API.
3. The **Optimizer** evaluates the output and algorithmically adjusts the Heater's temperature, calculating the Secant trajectory across multiple iterations until the Flash Vessel achieves exactly a 50% vapor fraction.
