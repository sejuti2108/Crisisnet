"""
Fire escalation severity module.

Rule-based heuristic (no ML — no suitable labeled dataset exists for this
specific feature combination; see project documentation for justification).
Backend-agnostic — no Django dependency.
"""

MATERIAL_RISK_WEIGHT = 40
ROAD_ACCESS_NARROW_WEIGHT = 30
ROAD_ACCESS_MEDIUM_WEIGHT = 15
DENSITY_RISK_WEIGHT = 20
TIME_OF_DAY_RISK_WEIGHT = 10
COMPOUNDING_PENALTY = 15

# Occupancy type weights — tiered by real-world severity, not treated uniformly.
OCCUPANCY_WEIGHTS = {
    "chemical": 45,
    "garment_factory": 35,
    "mall": 25,
    "industrial": 20,
    "residential": 0,
    "other": 0,
}

# Minimum guaranteed risk LABEL for certain occupancy types, regardless of
# how favorable the other factors are. Explosion/toxic-fume risk at a
# chemical facility doesn't get "averaged out" by a wide road or daytime
# timing — the hazard is inherent to what's stored there, not just how
# fast it might spread or how easily trucks can reach it.
OCCUPANCY_RISK_FLOOR_LABEL = {
    "chemical": "High Escalation Risk",
    # garment_factory intentionally has no floor — high weight (35) already
    # pushes it toward Medium/High under normal conditions, but unlike
    # chemical, there's no standalone explosion/toxicity hazard that
    # justifies ignoring favorable road/time/density conditions entirely.
}

HIGH_RISK_THRESHOLD = 85
MEDIUM_RISK_THRESHOLD = 45

COMBUSTIBLE_MATERIALS = {"tin", "wood", "bamboo"}
HIGH_DENSITY_CATEGORIES = {"slum", "high_density"}

_LABEL_RANK = {"Standard Risk": 0, "Medium Escalation Risk": 1, "High Escalation Risk": 2}


def calculate_fire_severity(
    material: str,
    road_access: str,
    density: str,
    time_of_day: int,
    occupancy_type: str = "other",
) -> dict:
    """
    Estimate fire escalation risk from distress-call intake parameters.

    Args:
        material: Building material, e.g. "tin", "wood", "bamboo", "concrete".
        road_access: "narrow_alley" | "medium_road" | "wide_road" (or similar).
        density: "slum" | "high_density" | "residential" | "low_density".
        time_of_day: Hour of day, 0-23.
        occupancy_type: "chemical" | "garment_factory" | "mall" | "industrial" |
            "residential" | "other" (default).

    Returns:
        dict with:
            - "score": int, raw weighted score (before any floor is applied)
            - "label": final risk label, after applying any occupancy-type floor
            - "factors": dict breaking down each contributing component
            - "floor_applied": bool, True if the occupancy-type floor raised
              the label above what the raw score alone would have produced

    Raises:
        ValueError: if time_of_day is invalid, or occupancy_type is unrecognized.
    """
    if not isinstance(time_of_day, int) or not (0 <= time_of_day <= 23):
        raise ValueError(f"time_of_day must be an integer 0-23, got {time_of_day!r}")

    material = (material or "").strip().lower()
    road_access = (road_access or "").strip().lower()
    density = (density or "").strip().lower()
    occupancy_type = (occupancy_type or "other").strip().lower()

    if occupancy_type not in OCCUPANCY_WEIGHTS:
        raise ValueError(
            f"Unrecognized occupancy_type: {occupancy_type!r}. "
            f"Expected one of {sorted(OCCUPANCY_WEIGHTS)}"
        )

    factors = {}

    is_combustible = material in COMBUSTIBLE_MATERIALS
    factors["material"] = MATERIAL_RISK_WEIGHT if is_combustible else 0

    is_narrow_access = road_access == "narrow_alley"
    if is_narrow_access:
        factors["road_access"] = ROAD_ACCESS_NARROW_WEIGHT
    elif road_access == "medium_road":
        factors["road_access"] = ROAD_ACCESS_MEDIUM_WEIGHT
    else:
        factors["road_access"] = 0

    is_high_density = density in HIGH_DENSITY_CATEGORIES
    factors["density"] = DENSITY_RISK_WEIGHT if is_high_density else 0

    is_night = time_of_day >= 23 or time_of_day <= 5
    factors["time_of_day"] = TIME_OF_DAY_RISK_WEIGHT if is_night else 0

    factors["occupancy_type"] = OCCUPANCY_WEIGHTS[occupancy_type]

    is_worst_case_structural = is_combustible and is_narrow_access and is_high_density
    factors["compounding_penalty"] = COMPOUNDING_PENALTY if is_worst_case_structural else 0

    risk_score = sum(factors.values())

    # Classify from the raw score first
    if risk_score >= HIGH_RISK_THRESHOLD:
        computed_label = "High Escalation Risk"
    elif risk_score >= MEDIUM_RISK_THRESHOLD:
        computed_label = "Medium Escalation Risk"
    else:
        computed_label = "Standard Risk"

    # Apply occupancy-type floor, if one exists — raises the label if the
    # computed one is lower, never lowers it.
    floor_label = OCCUPANCY_RISK_FLOOR_LABEL.get(occupancy_type)
    floor_applied = False
    if floor_label is not None and _LABEL_RANK[floor_label] > _LABEL_RANK[computed_label]:
        final_label = floor_label
        floor_applied = True
    else:
        final_label = computed_label

    return {
        "score": risk_score,
        "label": final_label,
        "factors": factors,
        "floor_applied": floor_applied,
    }


if __name__ == "__main__":
    test_cases = [
        {"material": "wood", "road_access": "narrow_alley", "density": "slum",
         "time_of_day": 2, "occupancy_type": "garment_factory"},
        {"material": "concrete", "road_access": "narrow_alley", "density": "high_density",
         "time_of_day": 14, "occupancy_type": "chemical"},
        # The key test case: chemical facility with EVERY favorable condition
        # (fireproof material, wide road, low density, daytime) — should
        # still come back High, because of the floor.
        {"material": "concrete", "road_access": "wide_road", "density": "residential",
         "time_of_day": 14, "occupancy_type": "chemical"},
        {"material": "concrete", "road_access": "wide_road", "density": "residential",
         "time_of_day": 14, "occupancy_type": "other"},
    ]
    for case in test_cases:
        result = calculate_fire_severity(**case)
        print(f"Input: {case}\n  -> {result}\n")