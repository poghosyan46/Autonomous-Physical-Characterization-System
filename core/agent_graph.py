import os
import sys
import json
import logging
import requests
import numpy as np
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

from core.ossila_connector import get_shared_connector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AdaptiveAgent")

os.makedirs("data", exist_ok=True)
connector = get_shared_connector(port="COM3")
experimental_results = {}

np_trapz = getattr(np, 'trapezoid', getattr(np, 'trapz', None))


@tool
def measure_2point_resistance_tool(v_applied: float = 0.5) -> str:
    """Measures 2-probe baseline current and resistance."""
    res = connector.measure_point(voltage=v_applied)
    if res["status"] == "success":
        curr = abs(res["current_A"])
        res["resistance_2probe_Ohm"] = float(abs(res["voltage_V"]) / curr) if curr > 1e-11 else float("inf")
    experimental_results["resistance_2point"] = res
    return json.dumps(res, indent=2)


@tool
def sweep_voltage_tool(start_v: float = -1.0, stop_v: float = 1.0, steps: int = 15) -> str:
    """Executes safe linear I-V sweep [-1V to +1V]."""
    res = connector.sweep_voltage(start_v=start_v, stop_v=stop_v, steps=steps)
    experimental_results["iv_sweep"] = res
    if res["status"] == "success":
        pts = res["data"]
        v_arr = np.array([p["voltage_V"] for p in pts])
        i_arr = np.array([p["current_A"] for p in pts])
        di_dv = np.gradient(i_arr, v_arr) if len(v_arr) > 1 else np.array([0])
        max_idx = int(np.argmax(np.abs(di_dv)))
        crit_v = float(v_arr[max_idx]) if len(v_arr) > 0 else 0.0
        return json.dumps({
            "status": "success",
            "count": len(pts),
            "max_current_A": float(np.max(np.abs(i_arr))) if len(i_arr) > 0 else 0.0,
            "adaptive_trigger": {"critical_voltage_V": crit_v}
        }, indent=2)
    return json.dumps(res, indent=2)


@tool
def adaptive_fine_sweep_tool(center_v: float = 0.2, span_v: float = 0.4, step_v: float = 0.05) -> str:
    """Performs localized high-density scan."""
    start_v = max(-1.0, center_v - span_v / 2.0)
    stop_v = min(1.0, center_v + span_v / 2.0)
    steps = int(np.abs(stop_v - start_v) / step_v) + 1
    res = connector.sweep_voltage(start_v=start_v, stop_v=stop_v, steps=steps)
    experimental_results["adaptive_fine_sweep"] = res
    return json.dumps({"status": "success", "count": steps, "center_v_scanned": center_v}, indent=2)


@tool
def hysteresis_sweep_tool(v_max: float = 1.0, steps_per_branch: int = 6) -> str:
    """Executes cyclic hysteresis sweep from -v_max to +v_max."""
    res = connector.hysteresis_sweep(v_max=v_max, steps_per_branch=steps_per_branch)
    experimental_results["hysteresis"] = res
    if res["status"] == "success":
        pts = res["data"]
        v_arr = np.array([p["voltage_V"] for p in pts])
        i_arr = np.array([p["current_A"] for p in pts])
        area = float(np.abs(np_trapz(i_arr, v_arr))) if len(v_arr) > 1 else 0.0
        return json.dumps({"status": "success", "count": len(pts), "hysteresis_loop_area_VA": area}, indent=2)
    return json.dumps(res, indent=2)


@tool
def measure_time_series_it_tool(v_bias: float = 0.5, duration_sec: float = 5.0, interval_sec: float = 0.5) -> str:
    """Measures dynamic time-series I(t) under safe bias."""
    res = connector.measure_time_series_it(v_bias=v_bias, duration_sec=duration_sec, interval_sec=interval_sec)
    experimental_results["time_series_it"] = res
    return json.dumps({"status": "success", "count": res.get("count", 0)}, indent=2)


tools = [measure_2point_resistance_tool, sweep_voltage_tool, adaptive_fine_sweep_tool, hysteresis_sweep_tool, measure_time_series_it_tool]
tools_by_name = {t.name: t for t in tools}


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


SYSTEM_PROMPT = (
    "You are an autonomous AI experimental physicist characterizing a 5nm Ag/Si thin film sample on COM3 using an Ossila SMU.\n"
    "Follow this exact safe voltage sequence:\n"
    "1. measure_2point_resistance_tool(v_applied=0.5)\n"
    "2. sweep_voltage_tool(start_v=-1.0, stop_v=1.0, steps=15)\n"
    "3. Read critical_voltage_V from step 2 output, then run adaptive_fine_sweep_tool(center_v=critical_voltage_V)\n"
    "4. hysteresis_sweep_tool(v_max=1.0)\n"
    "5. measure_time_series_it_tool(v_bias=0.5, duration_sec=5.0)"
)


def call_model(state: AgentState) -> Dict[str, Any]:
    print("\n🧠 [AI AGENT] Querying LLM Reasoning Engine...", flush=True)
    if "GROQ_API_KEY" in os.environ:
        try:
            llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.0)
            llm_with_tools = llm.bind_tools(tools)
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            logger.warning(f"Groq API Error ({e}). Switching to Local Ollama SLM Fallback...")

    try:
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + [
                {"role": "user", "content": m.content} for m in state["messages"]
            ],
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            content = res.json().get("message", {}).get("content", "")
            return {"messages": [BaseMessage(content=content, type="ai")]}
    except Exception as local_err:
        logger.error(f"Local Ollama SLM unavailable: {local_err}")

    raise RuntimeError("Neither Groq Cloud API nor Local Ollama SLM is available.")


def call_tool(state: AgentState) -> Dict[str, Any]:
    last_message = state["messages"][-1]
    tool_responses = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        print(f"🔧 [TOOL CALL] Agent invoking tool: {tool_name} with args {tool_call.get('args', {})}", flush=True)
        selected_tool = tools_by_name[tool_name]
        obs = selected_tool.invoke(tool_call["args"])
        tool_responses.append(ToolMessage(content=str(obs), tool_call_id=tool_call["id"]))
    return {"messages": tool_responses}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tool)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app = workflow.compile()


def run_agent_pipeline():
    print("🚀 Starting Autonomous Closed-Loop Agent Execution...", flush=True)
    
    for fname in ["experiment_data.json", "physics_summary.json", "plots_output.png", "report.pdf"]:
        fpath = os.path.join("data", fname)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    experimental_results.clear()
    initial_input = {
        "messages": [HumanMessage(content="Conduct full physical characterization of 5nm Ag/Si thin film sample on COM3.")]
    }
    
    chat_log = []
    try:
        for event in app.stream(initial_input, stream_mode="values"):
            if "messages" in event:
                for msg in event["messages"]:
                    msg_type = getattr(msg, "type", "unknown")
                    content = getattr(msg, "content", "")
                    tool_calls = getattr(msg, "tool_calls", [])
                    
                    entry = {
                        "type": msg_type,
                        "content": str(content) if content else "",
                        "tool_calls": tool_calls
                    }
                    if not chat_log or chat_log[-1] != entry:
                        chat_log.append(entry)
    except Exception as e:
        print(f"❌ Exception during agent execution: {e}", flush=True)
        return None

    experimental_results["agent_chat_log"] = chat_log

    output_path = os.path.join("data", "experiment_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(experimental_results, f, indent=2)
    print(f"\n✅ Successfully completed measurement cycle & saved {output_path}", flush=True)
    return experimental_results


if __name__ == "__main__":
    run_agent_pipeline()