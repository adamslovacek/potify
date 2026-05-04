"""Planter sleeve generator package."""

__all__ = ["build_planter_sleeve", "ExportFormat", "GeneratorConfig"]


def __getattr__(name: str):
    if name in {"build_planter_sleeve", "ExportFormat", "GeneratorConfig"}:
        from .model import ExportFormat, GeneratorConfig, build_planter_sleeve

        exports = {
            "build_planter_sleeve": build_planter_sleeve,
            "ExportFormat": ExportFormat,
            "GeneratorConfig": GeneratorConfig,
        }
        return exports[name]
    raise AttributeError(f"module 'planter_generator' has no attribute {name!r}")
