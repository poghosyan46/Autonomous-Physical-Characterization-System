import os
import sys
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from core.ossila_connector import get_shared_connector
from core.agent_graph import run_agent_pipeline
from core.physics_analysis import run_physics_analysis
from services.generate_plots import generate_scientific_plots
from services.generate_report import generate_pdf_report

logger = logging.getLogger("BackendMain")

app = FastAPI(
    title="Autonomous SMU Physical Characterization API",
    version="1.0.0",
    description="Backend API for Ossila SMU Hardware Control & LangGraph AI Agent"
)

pipeline_status = {"status": "idle", "message": "System ready"}


def get_connector():
    return get_shared_connector(port="COM3")


class MeasureRequest(BaseModel):
    voltage: float = 2.0
    channel: Optional[str] = "smu1"


class SweepRequest(BaseModel):
    start_v: float = -5.0
    stop_v: float = 5.0
    steps: int = 31


@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Autonomous AI Physics Lab",
        "hardware_port": "COM3"
    }


@app.get("/api/v1/hardware/status")
def get_hardware_status():
    """Checks COM port availability and hardware status."""
    try:
        conn = get_connector()
        s = conn._get_serial()
        return {"status": "success", "port": "COM3", "connected": s.is_open}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/v1/agent/status")
def get_agent_status():
    """Returns dynamic status of background agent pipeline execution."""
    return pipeline_status


@app.post("/api/v1/hardware/measure")
def measure_single_point(req: MeasureRequest):
    """Executes single point voltage/current measurement."""
    conn = get_connector()
    res = conn.measure_point(voltage=req.voltage, channel=req.channel)
    if res.get("status") == "error":
        raise HTTPException(status_code=500, detail=res.get("message"))
    return res


@app.post("/api/v1/hardware/sweep")
def execute_voltage_sweep(req: SweepRequest):
    """Executes dynamic voltage sweep."""
    conn = get_connector()
    res = conn.sweep_voltage(start_v=req.start_v, stop_v=req.stop_v, steps=req.steps)
    return res


def full_pipeline_task():
    """Background task to run full agent pipeline safely and track progress."""
    global pipeline_status
    try:
        pipeline_status = {"status": "running", "message": "Executing SMU hardware sweeps..."}
        run_agent_pipeline()
        
        pipeline_status = {"status": "running", "message": "Analyzing physics & generating plots..."}
        run_physics_analysis()
        generate_scientific_plots()
        generate_pdf_report()
        
        pipeline_status = {"status": "completed", "message": "Measurement finished successfully!"}
    except Exception as e:
        logger.error(f"Error during agent pipeline execution: {e}")
        pipeline_status = {"status": "error", "message": str(e)}


@app.post("/api/v1/agent/run")
def trigger_agent_pipeline(background_tasks: BackgroundTasks):
    """Triggers autonomous closed-loop LangGraph agent execution."""
    global pipeline_status
    if pipeline_status.get("status") == "running":
        return {"status": "already_running", "message": "Pipeline is already executing."}
    
    pipeline_status = {"status": "running", "message": "Starting Agent execution..."}
    background_tasks.add_task(full_pipeline_task)
    return {
        "status": "initiated",
        "message": "Autonomous Agent execution started in background."
    }


@app.get("/api/v1/report/download")
def download_pdf_report():
    """Returns generated PDF characterization report."""
    pdf_path = os.path.join(ROOT_DIR, "data", "report.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report PDF not generated yet.")
    return FileResponse(pdf_path, media_type="application/pdf", filename="characterization_report.pdf")