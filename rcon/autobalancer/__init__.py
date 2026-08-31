"""Fair, squad-aware team-size balancing for CRCON.

The package deliberately keeps rating and planning free of RCON/Redis side effects so
operators can shadow-test a policy before enabling player switches.
"""

from .planner import build_plan, build_strength_swap_recommendations, required_switches

__all__ = ["build_plan", "build_strength_swap_recommendations", "required_switches"]
