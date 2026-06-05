"""Sanity checks on the FSISIM eval personas."""
from agent_server import personas


def test_personas_is_a_nonempty_list():
    assert isinstance(personas.PERSONAS, list)
    assert len(personas.PERSONAS) >= 5


def test_each_persona_has_required_keys():
    for p in personas.PERSONAS:
        assert "goal" in p and p["goal"]
        assert "persona" in p and p["persona"]
        assert "simulation_guidelines" in p
        assert isinstance(p["simulation_guidelines"], list)


def test_personas_cover_fsisim_domains():
    """At least one persona per major FSISIM system."""
    goals = " ".join(p["goal"].lower() for p in personas.PERSONAS)
    for domain in ["hydraulic", "motion", "visual", "fms", "connector"]:
        assert domain in goals, f"no persona for {domain}"
