"""Planter sleeve generator package."""

__all__ = [
		"DrainagePattern",
		"ExportFormat",
		"GeneratorConfig",
		"PrintProfile",
		"TextMode",
		"analyze_printability",
		"build_planter_sleeve",
		"repair_config_for_printability",
]


def __getattr__(name: str):
		if name in __all__:
				from . import model

				value = getattr(model, name)
				globals()[name] = value
				return value
		raise AttributeError(f"module 'planter_generator' has no attribute {name!r}")
