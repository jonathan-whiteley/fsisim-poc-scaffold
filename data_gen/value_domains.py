"""Categorical value pools for synthetic issue generation.

Seeds from 5 sample rows and expands realistically. Pools are tuned to a
typical FSISIM mix (rough 60/25/10/5 mechanical/software/electrical/other).
"""
from dataclasses import dataclass

ISSUE_TYPES = ["Mechanical", "Software", "Electrical", "Avionics"]
ISSUE_TYPE_WEIGHTS = [0.60, 0.25, 0.10, 0.05]

CATEGORIES_BY_TYPE = {
    "Mechanical": ["Hardware"],
    "Software": ["Software"],
    "Electrical": ["Hardware", "Electrical"],
    "Avionics": ["Avionics", "Software"],
}

SYSTEMS_BY_TYPE = {
    "Mechanical": ["Hydraulics", "Motion System", "Control Loading", "Cockpit Hardware"],
    "Software": ["Visual System", "Flight Model", "Instructor Operating Station", "Database"],
    "Electrical": ["Motion System", "Power Distribution", "Cockpit Wiring", "Visual System"],
    "Avionics": ["FMS", "Autopilot", "EICAS", "Navigation"],
}

ROOT_CAUSES = [
    "Worn actuator seal", "Loose connector", "Database corruption",
    "Configuration drift", "Hydraulic pump failure", "Sensor calibration drift",
    "Visual database mismatch", "Motor driver overheat", "Software regression",
    "Power supply fluctuation", "Loose ground strap", "Firmware version mismatch",
    "Cable degradation", "Cooling fan failure",
]

LOST_TIME_TYPES = ["Training", "Scheduled", "Non-Impact"]
LOST_TIME_TYPE_WEIGHTS = [0.55, 0.30, 0.15]

NOTE_TYPES = [
    ("INI", "Initial Report"),
    ("UPD", "Update"),
    ("SOL", "Solution"),
    ("RES", "Resolution"),
]

NOTE_CREATORS = [
    "John Smith", "Jane Doe", "Mike Johnson", "Sarah Williams", "Tom Anderson",
    "Emily Chen", "Robert Martinez", "Lisa Patel", "David Kim", "Karen O'Brien",
    "Alex Rivera", "Priya Singh",
]

ISSUE_CATEGORIES = ["Maintenance", "Operations", "Engineering"]
ISSUE_CATEGORY_WEIGHTS = [0.65, 0.25, 0.10]

DEVICE_STATUSES = ["Active", "Inactive", "In Service"]


@dataclass(frozen=True)
class SimulatorRecord:
    sim_id: int
    sim_name: str
    sim_type: int
    sim_type_name: str
    loc_name: str
    sim_location_id: int


SIMULATORS = [
    SimulatorRecord(501, "G001-SIM-01", 1, "Full Flight Simulator", "Washington", 10),
    SimulatorRecord(502, "G001-SIM-02", 1, "Full Flight Simulator", "St. George", 20),
    SimulatorRecord(503, "G001-SIM-03", 2, "Fixed Training Device", "Teterboro", 30),
    SimulatorRecord(504, "G001-SIM-04", 1, "Full Flight Simulator", "Tucson", 40),
    SimulatorRecord(505, "G001-SIM-05", 2, "Fixed Training Device", "Wichita", 50),
    SimulatorRecord(506, "G001-SIM-06", 1, "Full Flight Simulator", "Houston", 60),
    SimulatorRecord(507, "G001-SIM-07", 3, "Cockpit Procedures Trainer", "Memphis", 70),
    SimulatorRecord(508, "G001-SIM-08", 1, "Full Flight Simulator", "Atlanta", 80),
]
