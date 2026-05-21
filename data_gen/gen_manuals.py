"""Generate synthetic FSISIM technical manual PDFs.

Each manual is a small markdown doc rendered to PDF via weasyprint. Every page
is watermarked 'SAMPLE / NOT REAL' so they cannot be mistaken for FSISIM internal
documents.

Section content is authored by Sonnet 4.5 via the Databricks Foundation Model API
(no personal Anthropic key required).
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import markdown as md
from weasyprint import HTML, CSS


@dataclass(frozen=True)
class ManualSpec:
    filename: str
    title: str
    outline: list[str]


MANUAL_SPECS: list[ManualSpec] = [
    ManualSpec(
        filename="fsisim_glossary.pdf",
        title="FSISIM Acronym & Term Glossary",
        outline=[
            "Aviation Acronyms (APU, FMC, FMS, IRS, ILS, RA, EICAS, ECAM, VNAV, LNAV)",
            "Simulator Hardware Terms (IOS, motion platform, control loading, visual system)",
            "Maintenance Terms (BIT, fault code, MMI, lost time categories)",
            "Note Type Codes (INI, UPD, SOL, RES)",
        ],
    ),
    ManualSpec(
        filename="hydraulic_system_manual.pdf",
        title="G001 Hydraulic System Reference Manual",
        outline=[
            "System Overview and Components",
            "Hydraulic Pressure Normal Operating Ranges",
            "Common Fault Codes and Indications",
            "Actuator Seal Inspection Procedure",
            "Troubleshooting Hydraulic Pressure Drops",
        ],
    ),
    ManualSpec(
        filename="motion_system_manual.pdf",
        title="G001 Motion System Reference Manual",
        outline=[
            "Motion Platform Architecture",
            "Motor Driver Boards and Connectors",
            "Motion Fault Codes (4xB Series)",
            "Connector Reseating Procedure",
            "Full Motion Test Checklist",
        ],
    ),
    ManualSpec(
        filename="visual_system_manual.pdf",
        title="G001 Visual System Reference Manual",
        outline=[
            "Visual Database Architecture",
            "Database Reload Procedure",
            "Terrain Rendering Diagnostics",
            "Common Airport Database Issues (KJFK, KSFO, EGLL)",
            "Display Calibration",
        ],
    ),
    ManualSpec(
        filename="maintenance_procedures.pdf",
        title="G001 Routine Maintenance Procedures",
        outline=[
            "Daily Pre-Use BIT Procedure",
            "Weekly Maintenance Checklist",
            "Parts Ordering and Vendor Coordination",
            "Lost Time Categorization Guidelines",
        ],
    ),
    ManualSpec(
        filename="simulator_specs.pdf",
        title="G001-SIM Series Specifications",
        outline=[
            "G001-SIM-01 through SIM-08 Configurations",
            "Simulator Type Classifications (Full Flight, Fixed Training, CPT)",
            "Site Locations and Lead Engineer Contacts",
            "Device Status Lifecycle (Active, Inactive, In Service)",
        ],
    ),
]


WATERMARK_CSS = """
@page {
  size: Letter;
  margin: 1in;
  @top-center {
    content: "SAMPLE / NOT REAL";
    color: #c00;
    font-size: 14pt;
    font-weight: bold;
    letter-spacing: 0.1em;
  }
  @bottom-center {
    content: "FSISIM POC Scaffold (synthetic content)";
    color: #888;
    font-size: 9pt;
  }
}
body { font-family: Roboto, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #222; }
h1 { color: #003865; font-size: 22pt; margin-bottom: 0.2em; }
h2 { color: #003865; font-size: 16pt; margin-top: 1.5em; }
h3 { color: #444; font-size: 13pt; }
"""


SYSTEM_PROMPT = (
    "You are writing sections of a fabricated flight simulator technical manual. "
    "Use realistic aviation and simulator jargon (APU, FMC, IRS, ILS, RA, FMS, VNAV, "
    "EICAS, ECAM, BIT, fault codes, etc.). Include at least one numbered procedure or "
    "bulleted list per section. 200-400 words. Markdown formatting. No headings (the "
    "section header is added separately). No disclaimers, no preamble, just the content."
)


def _default_authoring(section: str, manual_title: str) -> str:
    """Real authoring path: call Databricks FM API to write a section."""
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

    w = WorkspaceClient()
    user_msg = (
        f"Manual title: {manual_title}\n"
        f"Section: {section}\n\n"
        f"Write the section content now."
    )
    resp = w.serving_endpoints.query(
        name="databricks-claude-sonnet-4-5",
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content=SYSTEM_PROMPT),
            ChatMessage(role=ChatMessageRole.USER, content=user_msg),
        ],
        max_tokens=900,
    )
    return resp.choices[0].message.content.strip()


_author_section: Callable[[str, str], str] = _default_authoring


def _render_pdf(spec: ManualSpec, out_dir: Path) -> Path:
    body_md = [f"# {spec.title}\n"]
    for section in spec.outline:
        body_md.append(f"\n## {section}\n")
        body_md.append(_author_section(section, spec.title))
    html_body = md.markdown("\n".join(body_md))
    out_path = out_dir / spec.filename
    HTML(string=html_body).write_pdf(out_path, stylesheets=[CSS(string=WATERMARK_CSS)])
    return out_path


def generate_manuals(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [_render_pdf(spec, out_dir) for spec in MANUAL_SPECS]


if __name__ == "__main__":
    out = Path("./generated_manuals")
    paths = generate_manuals(out)
    for p in paths:
        print(p)
