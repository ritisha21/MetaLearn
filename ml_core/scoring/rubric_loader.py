"""
ml_core/scoring/rubric_loader.py

Loads and validates rubric YAML files (e.g. feynman_v1.yaml). Validation
happens at LOAD time, not at scoring time — a malformed rubric (weights
that don't sum to 1.0, a missing dimension) should fail loudly the moment
it's loaded, not silently produce a wrong composite score three calls
later when nobody's looking at the rubric file anymore.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

RUBRICS_DIR = Path(__file__).parent / "rubrics"


class RubricError(Exception):
    """Raised when a rubric file is missing, malformed, or internally
    inconsistent (e.g. weights that don't sum to 1.0)."""


@dataclass
class Dimension:
    name: str
    weight: float
    description: str
    scoring_guide: dict[str, str]


@dataclass
class Rubric:
    version: str
    dimensions: list[Dimension]
    overall_bands: dict[str, tuple[float, float]]

    def dimension_names(self) -> list[str]:
        return [d.name for d in self.dimensions]

    def weight_for(self, dimension_name: str) -> float:
        for d in self.dimensions:
            if d.name == dimension_name:
                return d.weight
        raise RubricError(f"Unknown dimension {dimension_name!r} for rubric {self.version!r}")


def load_rubric(name: str) -> Rubric:
    """
    Loads a rubric by name (e.g. "feynman_v1") from ml_core/scoring/rubrics/.
    Validates weight sum and required fields before returning — never
    returns a Rubric object that's internally inconsistent.
    """
    path = RUBRICS_DIR / f"{name}.yaml"
    if not path.exists():
        raise RubricError(f"Rubric file not found: {path}")

    try:
        raw = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise RubricError(f"Rubric file {path} is not valid YAML: {e}") from e

    if not isinstance(raw, dict) or "dimensions" not in raw:
        raise RubricError(f"Rubric file {path} is missing a top-level 'dimensions' key.")

    version = raw.get("rubric_version", name)
    dimensions: list[Dimension] = []

    for dim_name, dim_data in raw["dimensions"].items():
        if "weight" not in dim_data:
            raise RubricError(f"Dimension {dim_name!r} in {path} is missing a 'weight' field.")
        dimensions.append(
            Dimension(
                name=dim_name,
                weight=float(dim_data["weight"]),
                description=dim_data.get("description", ""),
                scoring_guide=dim_data.get("scoring_guide", {}),
            )
        )

    if not dimensions:
        raise RubricError(f"Rubric {path} defines zero dimensions.")

    weight_sum = sum(d.weight for d in dimensions)
    if abs(weight_sum - 1.0) > 0.001:
        raise RubricError(
            f"Rubric {path} dimension weights sum to {weight_sum:.4f}, not 1.0. "
            f"Weights: {[(d.name, d.weight) for d in dimensions]}"
        )

    overall_bands = {}
    for band_name, band_range in raw.get("overall_bands", {}).items():
        if not isinstance(band_range, list) or len(band_range) != 2:
            raise RubricError(f"overall_bands.{band_name} in {path} must be a [low, high] pair.")
        overall_bands[band_name] = (float(band_range[0]), float(band_range[1]))

    return Rubric(version=version, dimensions=dimensions, overall_bands=overall_bands)


def band_for_score(rubric: Rubric, score: float) -> str:
    """Returns the label (e.g. 'developing', 'excellent') for a composite
    score, based on the rubric's overall_bands. Returns 'unknown' if no
    band matches — deliberately not raising here, since a slightly
    out-of-range score (e.g. exactly 1.0 vs a band defined as [0.85, 1.0)
    boundary edge case) showing as 'unknown' is a far better failure mode
    for a results screen than crashing the whole results computation."""
    for band_name, (low, high) in rubric.overall_bands.items():
        if low <= score <= high:
            return band_name
    return "unknown"
