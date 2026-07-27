import os
import re
import sys
import subprocess
import time
import operator
from typing import TypedDict, Annotated, List, Tuple
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

# Load free API keys from .env file
load_dotenv()

# --- CONFIGURATION ---
DWSIM_INSTALL_PATH = r"C:\Users\Rayirth\AppData\Local\DWSIM"


# 1. Define the Graph State (The Memory)
class AgentState(TypedDict):
    target_chemical: str
    current_code: str
    error_logs: str
    past_errors: Annotated[list[str], operator.add] 
    iteration: int
    status: str
    history: List[Tuple[float, float]] # Stores (Temperature, Vapor_Fraction)


# 2. Initialize the Free LLMs
architect_llm = ChatGroq(
    model="openai/gpt-oss-120b", temperature=0.2
)

debugger_llm = ChatGroq(
    model="openai/gpt-oss-120b", temperature=0.1
)


# --- HELPER FUNCTIONS ---
def extract_python_code(llm_response: str) -> str:
    """Extracts raw python code from the LLM's markdown block formatting."""
    match = re.search(r"```python(.*?)```", llm_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    generic_match = re.search(r"```(.*?)```", llm_response, re.DOTALL)
    if generic_match:
        return generic_match.group(1).strip()

    return llm_response.strip()


# 3. Define the Agent Nodes
def flowsheet_architect(state: AgentState):
    print(f"\n--- [Iteration {state['iteration'] + 1}] ---")
    print("[Architect Agent] Drafting DWSIM flowsheet code...")

    prompt = f"""You are the Flowsheet Architect Agent in Project Genesis.
Write executable Python code using the DWSIM Automation API to simulate: {state['target_chemical']}.

CRITICAL REQUIREMENTS:
1. Your script MUST begin with this exact initialization block:

import sys
import os
import clr

dwsim_path = r"C:/Users/Rayirth/AppData/Local/DWSIM"
thermocs_path = r"C:/Users/Rayirth/AppData/Local/DWSIM/ThermoCS"

sys.path.append(dwsim_path)
sys.path.append(thermocs_path)
os.chdir(dwsim_path)

if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dwsim_path)
    os.add_dll_directory(thermocs_path)

# Force load all DWSIM dependencies into memory
clr.AddReference("CapeOpen")
clr.AddReference("DWSIM.Automation")
clr.AddReference("DWSIM.Interfaces")
clr.AddReference("DWSIM.GlobalSettings")
clr.AddReference("DWSIM.SharedClasses")
clr.AddReference("DWSIM.Thermodynamics")
clr.AddReference("ThermoCS")

from DWSIM.Automation import Automation3

interf = Automation3()
flowsheet = interf.CreateFlowsheet()

2. PROPERTY PACKAGES & API RULES:
   - To add a compound: flowsheet.AddCompound("Water")
   - To add Peng-Robinson: pp = flowsheet.CreateAndAddPropertyPackage("Peng-Robinson (PR)")
   - ABSOLUTE RULE: You MUST assign property packages ONLY to Material Streams using `stream.SetPropertyPackage(pp)`.
   - ABSOLUTE RULE: Unit operations like Heaters do NOT have a `SetPropertyPackage` method. Never assign property packages to them.
   - Do NOT wrap API calls in try/except blocks.

3. Return ONLY valid Python code, formatted inside a standard python markdown block.

4. MATERIAL STREAM SYNTAX:
   - You MUST import the ObjectType enum: 
     from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
   - To create a stream, add it to the flowsheet grid, then extract the stream object:
     stream_obj = flowsheet.AddObject(ObjectType.MaterialStream, 50, 50, "Feed Stream")
     feed_stream = stream_obj.GetAsObject()
   - Set Temperature (in Kelvin): feed_stream.SetTemperature(298.15)
   - Set Pressure (in Pascal): feed_stream.SetPressure(101325.0)
   - Set Mass Flow (in kg/s): feed_stream.SetMassFlow(10.0)
   
5. COMPOSITION SYNTAX:
   - You MUST import the .NET Array type to handle C# arrays in Python:
     from System import Array
   - You MUST set the molar fractions using a .NET float array for ALL compounds.
   - Syntax: 
     comp = Array[float]([0.5, 0.5])
     feed_stream.SetOverallMolarComposition(comp)

6. EXECUTION & DATA EXTRACTION:
   - feed_stream.Calculate()
   - interf.CalculateFlowsheet2(flowsheet)
   - Read states AFTER calculation: feed_stream.GetTemperature(), feed_stream.GetMassFlow()
   - You MUST print output values to the console so the System Node can capture them.

7. UNIT OPERATIONS SYNTAX:
   - You MUST load the unit operations library: `clr.AddReference("DWSIM.UnitOperations")`
   - Import: `from DWSIM.UnitOperations import UnitOperations`
   - To add a Heater: 
     heater_obj = flowsheet.AddObject(ObjectType.Heater, 150, 50, "Heater Block")
     heater = heater_obj.GetAsObject()
   - heater.CalcMode = UnitOperations.Heater.CalculationMode.OutletTemperature
   - heater.OutletTemperature = 358.15

8. ENERGY STREAMS:
   - energy_obj = flowsheet.AddObject(ObjectType.EnergyStream, 150, 100, "Heat Duty")
   - energy_stream = energy_obj.GetAsObject()

9. CONNECTION SYNTAX (CRITICAL RULE):
   - TOPOLOGY ABSOLUTE RULE: You CANNOT connect two unit operations directly. You MUST create an intermediate Material Stream between them. (e.g., Heater -> Intermediate Stream -> Flash Drum).
   - You MUST connect streams to unit operations using their Graphic Objects.
   - Use `-1, -1` for the port indices. DWSIM will auto-resolve the correct ports natively as long as you follow the topology rule!
   - Example: flowsheet.ConnectObjects(feed_obj.GraphicObject, heater_obj.GraphicObject, -1, -1)
   - Example: flowsheet.ConnectObjects(heater_obj.GraphicObject, inter_stream_obj.GraphicObject, -1, -1)
   - Example: flowsheet.ConnectObjects(inter_stream_obj.GraphicObject, flash_obj.GraphicObject, -1, -1)

10. FLASH VESSEL SYNTAX & CONNECTIONS:
    - Add Vessel: flash_obj = flowsheet.AddObject(ObjectType.Vessel, 350, 50, "Flash Drum")
    - Create THREE output/intermediate streams: intermediate_feed, vapor_obj, and liquid_obj.
    - ABSOLUTE RULE: Do NOT call `SetPressure()` or `SetTemperature()` on the Vessel object. It inherits the state from the intermediate feed stream automatically.
    - Connect Vessel to Products: 
      flowsheet.ConnectObjects(flash_obj.GraphicObject, vapor_obj.GraphicObject, -1, -1)
      flowsheet.ConnectObjects(flash_obj.GraphicObject, liquid_obj.GraphicObject, -1, -1)

11. NAMESPACE IMPORT RESTRICTIONS:
    - NEVER use `import DWSIM.UnitOperations` or `from DWSIM import UnitOperations` as standard imports. Use `clr.AddReference` first.
"""

    if state.get("past_errors"):
        prompt += "\n\nHISTORY OF PREVIOUS FAILURES (SLIDING WINDOW):\n"
        
        # --- SLIDING WINDOW FIX ---
        # Keep only the last 2 errors to prevent token limits (Error 429/413)
        recent_errors = state["past_errors"][-2:] 
        
        for i, past_err in enumerate(recent_errors):
            prompt += f"\n--- Recent Attempt {i+1} ---\n{past_err}\n"
            
        prompt += "\nCRITICAL: Do NOT repeat the mistakes or use the exact same code from the previous attempts. Follow the connection and property package rules strictly."

    response = architect_llm.invoke([HumanMessage(content=prompt)])

    time.sleep(30)

    return {
        "current_code": response.content,
        "iteration": state["iteration"] + 1,
    }


def simulation_executor(state: AgentState):
    print("\n[System Node] Executing flowsheet code in DWSIM...")

    raw_code = extract_python_code(state["current_code"])

    temp_filename = "temp_sim.py"
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(raw_code)

    try:
        result = subprocess.run(
            [sys.executable, temp_filename], 
            capture_output=True,
            text=True,
            timeout=90,
        )

        if result.returncode != 0:
            print("\n[System Node] 🛑 Execution Failed! Capturing error log for Debugger...")
            error_msg = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            return {"error_logs": error_msg, "status": "failed"}
        else:
            print("\n[System Node] ✅ Execution Successful! Passing to Optimizer...")
            # Capture the terminal output so the optimizer can read the Vapor Fraction
            return {"error_logs": result.stdout, "status": "success"}

    except subprocess.TimeoutExpired:
        print("\n[System Node] ⏱️ Execution Timed Out!")
        return {
            "error_logs": "Execution timed out after 90 seconds.",
            "status": "failed"
        }
    except Exception as e:
        return {
            "error_logs": f"Subprocess system failure: {str(e)}", 
            "status": "failed"
        }


def system_debugger(state: AgentState):
    print("\n[Debugger Agent] Analyzing failure...")
    
    prompt = f"""You are the Debugger Agent. The following DWSIM code failed to execute.
Code:
{state['current_code']}

Error Logs:
{state['error_logs']}

Provide a short, specific diagnosis of why this failed and how to fix it."""

    response = debugger_llm.invoke([HumanMessage(content=prompt)])
    time.sleep(30)
    print(f"\n[Debugger Diagnosis]:\n{response.content[:200]}...\n")
    
    return {
        "error_logs": response.content,
        "past_errors": [f"Iteration {state['iteration']} failed. Debugger Diagnosis: {response.content}"]
    }


def optimizer_node(state: AgentState):
    print("\n[Optimizer Agent] Analyzing thermodynamic results...")
    
    terminal_output = state.get("error_logs", "") 
    current_code = state.get("current_code", "")
    
    try:
        vapor_match = re.search(r"Vapor flow rate:\s*([0-9.]+)", terminal_output)
        liquid_match = re.search(r"Liquid flow rate:\s*([0-9.]+)", terminal_output)
        
        v_flow = float(vapor_match.group(1)) if vapor_match else 0.0
        l_flow = float(liquid_match.group(1)) if liquid_match else 0.0
        
        total_flow = v_flow + l_flow
        actual_vf = v_flow / total_flow if total_flow > 0 else 0.0
        
    except Exception as e:
        print("[Optimizer Agent] Failed to parse flows. Sending back to Debugger.")
        return {"status": "failed", "error_logs": "Optimizer could not find Vapor/Liquid flow rate in output."}

    print(f"[Optimizer Agent] Current Vapor Fraction: {actual_vf:.4f} (Target: 0.5000)")
    
    if abs(actual_vf - 0.5) < 0.01:
        print("[Optimizer Agent] 🎯 TARGET ACHIEVED! Convergence successful.")
        return {"status": "converged"}

    history = state.get("history", [])
    temp_match = re.search(r"heater\.OutletTemperature\s*=\s*([0-9.]+)", current_code)
    current_temp = float(temp_match.group(1)) if temp_match else 358.15 # Defaults to 85C in K
    
    history.append((current_temp, actual_vf))
    next_temp = current_temp
    
    if len(history) == 1:
        error = 0.5 - actual_vf
        next_temp = current_temp + (error * 10) 
    else:
        t0, vf0 = history[-2]
        t1, vf1 = history[-1]
        
        if vf1 == vf0: 
            next_temp = current_temp - 1.0
        else:
            slope = (vf1 - vf0) / (t1 - t0)
            next_temp = t1 + (0.5 - vf1) / slope
            
    # Clamp bounds between 25C and 150C
    next_temp = max(298.15, min(423.15, next_temp))
    
    print(f"[Optimizer Agent] Adjusting Heater Temperature to: {next_temp:.2f} K")
    
    updated_code = re.sub(
        r"heater\.OutletTemperature\s*=\s*[0-9.]+", 
        f"heater.OutletTemperature = {next_temp:.2f}", 
        current_code
    )
    
    return {
        "current_code": updated_code, 
        "history": history,
        "status": "optimizing"
    }


# 4. Graph Routing Logic
def route_from_executor(state: AgentState):
    if state.get("iteration", 0) >= 15: 
        print("\n[Routing] Reached maximum iterations (15). Stopping.")
        return "end"
        
    if state.get("status") == "failed":
        return "debugger"
        
    if state.get("status") == "success":
        return "optimizer"

def route_from_optimizer(state: AgentState):
    if state.get("status") == "converged":
        return "end"
    # If not converged, loop back to the system executor with the new code
    return "executor"


# 5. Build the LangGraph Swarm
workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("architect", flowsheet_architect)
workflow.add_node("executor", simulation_executor)
workflow.add_node("debugger", system_debugger)
workflow.add_node("optimizer", optimizer_node)

# Set Entry Point
workflow.set_entry_point("architect")

# Define Workflow Edges
workflow.add_edge("architect", "executor")

# Route out of Executor
workflow.add_conditional_edges(
    "executor",
    route_from_executor,
    {
        "debugger": "debugger", 
        "optimizer": "optimizer", 
        "end": END
    }
)

# Route out of Debugger
workflow.add_edge("debugger", "architect")

# Route out of Optimizer
workflow.add_conditional_edges(
    "optimizer",
    route_from_optimizer,
    {
        "executor": "executor",
        "end": END
    }
)

app = workflow.compile()


# --- Main Entry Point ---
if __name__ == "__main__":
    initial_state = {
        "target_chemical": "Initialize a Peng-Robinson flowsheet with Water and Ethanol. Create a feed stream at 25°C, 1 atm, 10 kg/s, with a 50/50 molar composition. Connect it to a Heater set to 358.15 K. Create an intermediate material stream to connect the heater output to a Flash Vessel. Create vapor and liquid product streams and connect them to the flash drum. Calculate the flowsheet and print the mass flow and composition of both the vapor and liquid products.",
        "current_code": "",
        "error_logs": "",
        "past_errors": [], 
        "iteration": 0,
        "status": "pending",
        "history": [] 
    }

    print("Starting Project Genesis Swarm...")
    final_state = app.invoke(initial_state)

    print("\n================ FINAL RESULTS ================")
    print(f"Total Iterations: {final_state['iteration']}")
    if final_state.get("status") == "converged":
        print("Status: 🎯 SUCCESS - Optimizer achieved target separation! Script saved in temp_sim.py")
    else:
        print("Status: FAILED - Review final error logs or increase iteration count.")