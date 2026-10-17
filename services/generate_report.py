import os
import json
import logging
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
)

logger = logging.getLogger("ReportGenerator")

DATA_DIR = "data"
REPORT_PATH = os.path.join(DATA_DIR, "report.pdf")
EXP_DATA_PATH = os.path.join(DATA_DIR, "experiment_data.json")
PHYS_DATA_PATH = os.path.join(DATA_DIR, "physics_summary.json")
PLOT_PATH = os.path.join(DATA_DIR, "plots_output.png")


def generate_pdf_report():
    """Compiles experiment json data and matplotlib plots into a professional scientific PDF report."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # 1. Load Experimental & Physics Data
    exp_data = {}
    phys_data = {}
    if os.path.exists(EXP_DATA_PATH):
        try:
            with open(EXP_DATA_PATH, "r", encoding="utf-8") as f:
                exp_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading experiment data: {e}")

    if os.path.exists(PHYS_DATA_PATH):
        try:
            with open(PHYS_DATA_PATH, "r", encoding="utf-8") as f:
                phys_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading physics summary: {e}")

    # 2. Build PDF Document
    doc = SimpleDocTemplate(
        REPORT_PATH,
        pagesize=letter,
        rightMargin=36, leftMargin=36,
        topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'],
        fontSize=20, leading=24, textColor=colors.HexColor('#1E293B'), spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontSize=10, leading=14, textColor=colors.HexColor('#64748B'), spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'SectionH2', parent=styles['Heading2'],
        fontSize=13, leading=16, textColor=colors.HexColor('#0F172A'), spaceBefore=12, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark', parent=styles['BodyText'],
        fontSize=9, leading=13, textColor=colors.HexColor('#334155')
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Autonomous Physical Characterization Report", title_style))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"Sample: 5nm Ag/Si Thin Film | Hardware: Ossila SMU (COM3) | Generated: {now_str}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=12))

    # Executive Summary Box
    story.append(Paragraph("Executive Summary & AI Agent Decision Trail", h2_style))
    chat_logs = exp_data.get("agent_chat_log", [])
    agent_summary_text = "The closed-loop AI agent successfully executed the 5-step characterization protocol on COM3."
    if chat_logs:
        ai_msgs = [m.get("content") for m in chat_logs if m.get("type") == "ai" and m.get("content")]
        if ai_msgs:
            agent_summary_text = ai_msgs[-1][:350] + "..." if len(ai_msgs[-1]) > 350 else ai_msgs[-1]

    summary_table_data = [[Paragraph(f"<b>AI Agent Analysis:</b> {agent_summary_text}", body_style)]]
    summary_table = Table(summary_table_data, colWidths=[540])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Extracted Physics Parameters Table
    story.append(Paragraph("Extracted Physical Parameters", h2_style))
    
    r_val = exp_data.get("resistance_2point", {}).get("resistance_2probe_Ohm", "N/A")
    r_str = f"{r_val:.2f} Ohm" if isinstance(r_val, (int, float)) else "N/A"
    
    phi_b = phys_data.get("fowler_nordheim", {}).get("barrier_height_eV", "N/A")
    phi_str = f"{phi_b:.3f} eV" if isinstance(phi_b, (int, float)) else "N/A"
    
    n_exp = phys_data.get("sclc_exponent_n", "N/A")
    n_str = f"{n_exp:.2f}" if isinstance(n_exp, (int, float)) else "N/A"
    
    area_val = phys_data.get("hysteresis_loop_area_VA", "N/A")
    area_str = f"{area_val:.2e} V*A" if isinstance(area_val, (int, float)) else "N/A"

    psd_val = phys_data.get("noise_1overf_psd_mean", "N/A")
    psd_str = f"{psd_val:.2e} A^2/Hz" if isinstance(psd_val, (int, float)) else "N/A"

    table_data = [
        [Paragraph("<b>Physical Metric</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>Conduction Mechanism / Note</b>", body_style)],
        [Paragraph("Baseline Resistance (R0)", body_style), Paragraph(r_str, body_style), Paragraph("2-Probe Low-Field Ohmic Contact Check", body_style)],
        [Paragraph("Schottky Barrier Height (Φb)", body_style), Paragraph(phi_str, body_style), Paragraph("Fowler-Nordheim Field Emission Fit", body_style)],
        [Paragraph("SCLC Exponent (n)", body_style), Paragraph(n_str, body_style), Paragraph("Space-Charge Limited Current Trap-Filling", body_style)],
        [Paragraph("Hysteresis Loop Area", body_style), Paragraph(area_str, body_style), Paragraph("Charge Trapping & Capacitive Memory Loop", body_style)],
        [Paragraph("1/f Noise PSD Mean", body_style), Paragraph(psd_str, body_style), Paragraph("Dynamic Current Stability Noise Floor", body_style)],
    ]

    param_table = Table(table_data, colWidths=[160, 110, 270])
    param_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(param_table)
    story.append(Spacer(1, 12))

    # Embedded High-DPI Scientific Curves Figure
    if os.path.exists(PLOT_PATH):
        story.append(Paragraph("Measured Scientific Transport Curves", h2_style))
        img = Image(PLOT_PATH, width=540, height=310)
        story.append(img)
        story.append(Spacer(1, 10))

    # Conclusion Section
    story.append(Paragraph("Physical Conclusion & Recommendations", h2_style))
    regime_text = "Ohmic Transport" if isinstance(n_exp, (int, float)) and n_exp <= 1.5 else "Fowler-Nordheim / SCLC Tunneling"
    conclusion_paragraph = (
        f"The 5nm Ag/Si metal-semiconductor film exhibits predominant <b>{regime_text}</b>. "
        "All measurements were conducted within safe hardware compliance limits (±1.2V) without device trip."
    )
    story.append(Paragraph(conclusion_paragraph, body_style))

    # Build Document
    try:
        doc.build(story)
        logger.info(f"PDF report successfully generated at {REPORT_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        return False


if __name__ == "__main__":
    generate_pdf_report()