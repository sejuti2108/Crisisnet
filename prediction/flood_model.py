"""
Flood risk prediction module.

Loads a pre-trained RandomForest pipeline (trained on the Noushin Gauhar
Bangladesh flood dataset) and exposes a single clean prediction function.
Backend-agnostic — no Django dependency, can be called from anywhere.
"""

import os
import joblib

# Resolve path relative to this file, so it works regardless of
# where the caller's working directory is.
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "flood_prediction_pipeline.joblib")

_model = None  # lazy-loaded, so importing this module doesn't immediately hit disk


def _get_model():
    global _model
    if _model is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"Flood model not found at {_MODEL_PATH}. "
                "Make sure flood_prediction_pipeline.joblib is present in this directory."
            )
        _model = joblib.load(_MODEL_PATH)
    return _model


def predict_flood_risk(rainfall: float, relative_humidity: float, cloud_coverage: float) -> dict:
    """
    Predict flood risk from three weather inputs.

    Args:
        rainfall: Rainfall amount. Training data range: 0-2072 (no fixed upper cap enforced).
        relative_humidity: Relative humidity (%). Training data range: 34-97.
        cloud_coverage: Cloud coverage index. Training data range: 0-7.9 (not a percentage).

    Returns:
        dict with "flood_predicted", "confidence", "risk_label".
        Also includes "warnings": list[str] if any input falls outside the
        training data's observed range (prediction still runs, but may be
        less reliable for out-of-distribution inputs).

    Raises:
        ValueError: if any input is missing, non-numeric, or physically impossible.
    """
    for name, value in [
        ("rainfall", rainfall),
        ("relative_humidity", relative_humidity),
        ("cloud_coverage", cloud_coverage),
    ]:
        if value is None:
            raise ValueError(f"{name} is missing (None) — cannot run prediction.")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric, got {type(value).__name__}.")

    # Hard limits — physically impossible values, always rejected
    if rainfall < 0:
        raise ValueError(f"rainfall cannot be negative: {rainfall}")
    if not (0 <= relative_humidity <= 100):
        raise ValueError(f"relative_humidity must be 0-100: {relative_humidity}")
    if cloud_coverage < 0:
        raise ValueError(f"cloud_coverage cannot be negative: {cloud_coverage}")

    # Soft warnings — valid but outside what the model was trained on,
    # so predictions here are extrapolating and may be less trustworthy
    warnings = []
    if not (34 <= relative_humidity <= 97):
        warnings.append(
            f"relative_humidity={relative_humidity} is outside the training range (34-97)"
        )
    if cloud_coverage > 7.9:
        warnings.append(
            f"cloud_coverage={cloud_coverage} exceeds the training range (0-7.9) — "
            "check this isn't a percentage mistakenly passed in"
        )
    if rainfall > 2072:
        warnings.append(
            f"rainfall={rainfall} exceeds the training range (0-2072) — treating as valid but extreme"
        )

    model = _get_model()

    import pandas as pd
    input_df = pd.DataFrame(
        [[rainfall, relative_humidity, cloud_coverage]],
        columns=["Rainfall", "Relative_Humidity", "Cloud_Coverage"],
    )

    prediction = model.predict(input_df)[0]
    probabilities = model.predict_proba(input_df)[0]
    confidence = float(max(probabilities))
    
    # Probability of the flood class specifically (not just the winning class).
    # Look the index up from classes_ rather than assuming position, so it
    # stays correct if the class order ever changes on retraining.
    flood_index = list(model.classes_).index(1)
    flood_probability = float(probabilities[flood_index])

    result = {
        "flood_predicted": bool(prediction),
        "confidence": round(confidence, 3),
        "flood_probability": round(flood_probability, 3),
        "risk_label": "High" if prediction == 1 else "Low",
    }
    if warnings:
        result["warnings"] = warnings

    return result

if __name__ == "__main__":
    # Quick manual sanity check — run this file directly to smoke-test the module
    # without needing Django or any other backend running.
    test_cases = [
        {"rainfall": 600, "relative_humidity": 85, "cloud_coverage": 6.5},  # expect High
        {"rainfall": 20, "relative_humidity": 40, "cloud_coverage": 3.5},    # expect Low
    ]
    for case in test_cases:
        result = predict_flood_risk(**case)
        print(f"Input: {case} -> {result}")