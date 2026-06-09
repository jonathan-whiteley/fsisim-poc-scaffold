"""FSISIM eval personas for mlflow.genai.evaluate's ConversationSimulator.

Each persona drives a multi-turn simulated conversation. The simulator picks
turns based on `goal` (what the user wants) and `persona` (how they talk);
`simulation_guidelines` shape pacing and follow-up behavior.

Replace this file (or override via the eval_personas_file DAB variable) when
adapting to a different fleet / customer.
"""

PERSONAS: list[dict] = [
    {
        "goal": "Diagnose a hydraulic pressure drop on a G001 simulator during takeoff",
        "persona": (
            "A first-year FSISIM technician with mechanical aptitude but limited "
            "exposure to the G001 platform. Comfortable reading procedures, less "
            "comfortable interpreting raw fault codes."
        ),
        "simulation_guidelines": [
            "Start with a vague symptom report before asking for specific diagnostics.",
            "Ask follow-up questions about whether similar past issues exist before accepting a recommendation.",
        ],
    },
    {
        "goal": "Resolve a motion platform fault code 47B on G001-SIM-03",
        "persona": (
            "A senior technician who knows the motion subsystem well but wants to "
            "validate the AI's recommendation against prior issues before acting."
        ),
        "simulation_guidelines": [
            "Push back on the first answer and ask for cited past issues.",
            "Prefer concise responses; flag any answer over 5 sentences.",
        ],
    },
    {
        "goal": "Investigate visual database corruption at KJFK approach",
        "persona": (
            "A visual systems specialist troubleshooting reports of glitches on the "
            "KJFK approach scene; wants both prior-issue context and manual references."
        ),
        "simulation_guidelines": [
            "Ask whether the issue is on a specific runway or scene-wide.",
            "Request a manual page citation, not just a summary.",
        ],
    },
    {
        "goal": "Understand what FMS VNAV means in the context of G001 sims",
        "persona": (
            "A new hire from a non-aviation background; encountered FMS VNAV in a "
            "ticket and needs the term explained in technician-friendly language."
        ),
        "simulation_guidelines": [
            "Avoid asking about specific fault codes; focus on concept clarification.",
            "Confirm understanding by asking for a real-world example.",
        ],
    },
    {
        "goal": "Find the documented procedure for reseating a hydraulic connector",
        "persona": (
            "An experienced FSISIM tech who wants the exact manual procedure rather "
            "than improvising; will reject AI-invented steps."
        ),
        "simulation_guidelines": [
            "Demand a specific manual + page number citation.",
            "If the AI tries to summarize a procedure without citing the manual, push back.",
        ],
    },
]
