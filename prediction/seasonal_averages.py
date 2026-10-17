"""
Historical seasonal averages, computed once from the training dataset,
used as the default/fallback weather input for flood prediction when no
manual entry has been provided for a station.

This is a two-step process:
  1. (Run once, offline) generate_seasonal_averages() reads the full
     FloodPrediction.csv and writes out a small JSON lookup file.
  2. (Run at request time) get_seasonal_average() reads that small JSON
     file — fast, no pandas/full-dataset dependency needed at runtime.

This split matters because the full CSV is a training-time artifact;
nothing serving predictions later should need to load it.
"""

import json
import os

_AVERAGES_PATH = os.path.join(os.path.dirname(__file__), "seasonal_averages.json")

_cache = None  # lazy-loaded, like flood_model.py's _model


def generate_seasonal_averages(csv_path: str, output_path: str = None) -> None:  # type: ignore
    """
    One-time generation step: reads the full training CSV and computes,
    for each (station, month) pair, the average Rainfall, Relative_Humidity,
    and Cloud_Coverage across all years in the dataset.

    Only needs to be run once (or re-run if the dataset changes) — not
    part of the normal prediction request path.

    Args:
        csv_path: path to FloodPrediction.csv
        output_path: where to write the resulting JSON lookup. Defaults
            to seasonal_averages.json next to this file.
    """
    import pandas as pd

    output_path = output_path or _AVERAGES_PATH

    df = pd.read_csv(csv_path)
    # Weather averages don't need the flood label, so use every row with complete
    # weather values. Restricting to labeled rows biases averages toward flood season.
    df = df.dropna(subset=["Rainfall", "Relative_Humidity", "Cloud_Coverage"])

    grouped = (
        df.groupby(["Station_Names", "Month"])[["Rainfall", "Relative_Humidity", "Cloud_Coverage"]]
        .mean()
        .round(2)
    )

    # Reshape into {station: {month: {...}}} for easy lookup
    averages = {}
    for (station, month), row in grouped.iterrows():
        averages.setdefault(station, {})[str(int(month))] = {
            "rainfall": row["Rainfall"],
            "relative_humidity": row["Relative_Humidity"],
            "cloud_coverage": row["Cloud_Coverage"],
        }

    with open(output_path, "w") as f:
        json.dump(averages, f, indent=2)

    print(f"Seasonal averages for {len(averages)} stations written to {output_path}")


def _load_averages() -> dict:
    global _cache
    if _cache is None:
        if not os.path.exists(_AVERAGES_PATH):
            raise FileNotFoundError(
                f"seasonal_averages.json not found at {_AVERAGES_PATH}. "
                "Run generate_seasonal_averages() once against the training "
                "CSV to create it."
            )
        with open(_AVERAGES_PATH) as f:
            _cache = json.load(f)
    return _cache


def get_seasonal_average(station_name: str, month: int) -> dict | None:
    """
    Look up the historical average weather for a station in a given month.

    Args:
        station_name: must match a name in stations.py exactly.
        month: 1-12.

    Returns:
        dict with "rainfall", "relative_humidity", "cloud_coverage", or
        None if this station/month combination has no historical data
        (e.g. a station with incomplete records for that month).
    """
    averages = _load_averages()
    station_data = averages.get(station_name)
    if station_data is None:
        return None
    return station_data.get(str(month))


if __name__ == "__main__":
    # One-time generation — update this path to wherever your CSV actually lives
    generate_seasonal_averages(
        csv_path=r"E:\3-2\3200\\CrisisNet\Crisisnet\prediction\FloodPrediction.csv"  # <-- update this accordingly
    )

    # Quick smoke test after generation
    result = get_seasonal_average("Rajshahi", 7)  # July
    print(f"Rajshahi, July average: {result}")