# prediction

Flood-risk prediction, fire-escalation scoring, live station weather overrides, and the operational Leaflet map for CrisisNet. The core ML and scoring modules (`flood_model.py`, `fire_severity.py`, `stations.py`, `seasonal_averages.py`, `assemble_map_data.py`) have no Django dependency and can be tested standalone.

## Setup

Python 3.10 or newer is required.

```bash
pip install -r prediction/requirements.txt
```

The versions in `requirements.txt` are pinned on purpose. `flood_prediction_pipeline.joblib` is a pickled scikit-learn pipeline and only loads cleanly on the scikit-learn version it was trained with (`1.7.2`). Only load `.joblib` files from this repository, since pickle files can execute code when loaded.

All standalone commands below are run from the folder that contains `manage.py`, using `python -m`.

## What is here

| File | Purpose |
|---|---|
| `flood_model.py` | `predict_flood_risk()`: flood risk inference from weather values |
| `fire_severity.py` | `calculate_fire_severity()`: rule-based fire escalation score |
| `stations.py` | The 33 Bangladesh weather stations (name, lat, lon) and nearest-station lookup |
| `seasonal_averages.py` | Per-station, per-month historical weather averages, used as default baseline |
| `seasonal_averages.json` | Precomputed output of the above, committed so runtime doesn't need the full CSV |
| `assemble_map_data.py` | Combines flood predictions and overrides into the map JSON payload |
| `models.py` & `forms.py` | `WeatherOverride` model (unique per station) and input form |
| `views.py` & `urls.py` | Django routes (`/map/`, `/map/data/`, `/map/weather/`, `/map/weather/reset/<id>/`) |
| `signals.py` & `apps.py` | Broadcasts `weather_update` and `site_update` over `/ws/alerts/` on model changes |
| `templates/prediction/` | `map.html` (Leaflet map) and `weather_overrides.html` (Coordinator/Admin override UI) |
| `static/prediction/` | `map.js`, `map.css`, and vendored Leaflet assets (`vendor/leaflet/`) |
| `tests.py` | Unit, view, and async `WebsocketCommunicator` tests (`python manage.py test prediction`) |
| `generate_sample_payload.py` | Generates standalone `map_prototype/sample_payload.json` for offline fixture reference |
| `model_training.ipynb` | How the flood model was trained and evaluated |
| `flood_prediction_pipeline.joblib` | The trained scikit-learn Random Forest pipeline |

## Using the core modules

```python
from prediction.flood_model import predict_flood_risk
from prediction.fire_severity import calculate_fire_severity
from prediction.assemble_map_data import build_map_payload, get_shelter_flood_risk
```

### Flood risk

```python
predict_flood_risk(rainfall=600, relative_humidity=85, cloud_coverage=6.5)
# {'flood_predicted': True, 'confidence': 1.0, 'flood_probability': 1.0, 'risk_label': 'High'}
```

| Input | Training range | Notes |
|---|---|---|
| `rainfall` | 0 to 2072 | Must be 0 or more |
| `relative_humidity` | 34 to 97 | Percent. Must be 0 to 100 |
| `cloud_coverage` | 0 to 7.9 | An index, not a percentage |

Impossible values (negative rainfall, humidity above 100, missing or non-numeric input) raise `ValueError`. Values that are physically possible but outside the training range still produce a prediction, with a `warnings` list added to the result.

`flood_probability` is the probability of the flood class (`1.0`) and is used for map coloring and sorting. `confidence` is the probability of whichever class won.

### Fire severity

```python
calculate_fire_severity(
    material="wood", road_access="narrow_alley", density="slum",
    time_of_day=2, occupancy_type="garment_factory",
)
# {'score': 150, 'label': 'High Escalation Risk', 'factors': {...}, 'floor_applied': False}
```

| Input | Accepted values |
|---|---|
| `material` | `tin`, `wood`, `bamboo` count as combustible; `concrete` does not |
| `road_access` | `narrow_alley`, `medium_road`, `wide_road` |
| `density` | `slum`, `high_density` count as dense; `residential`, `low_density` do not |
| `time_of_day` | Integer hour, 0 to 23 |
| `occupancy_type` | `chemical`, `garment_factory`, `mall`, `industrial`, `residential`, `other` (default) |

A `chemical` facility is always rated `High Escalation Risk`, regardless of other inputs (`floor_applied: True` when raised above raw score). In Django, `Incident.get_fire_assessment()` invokes this function dynamically for active fire incidents.

### Django map & live overrides

* `/map/` renders the authenticated operational map (Esri WorldStreetMap tiles + local Leaflet bundle).
* `/map/data/` combines:
  1. Flood predictions for the 33 stations (`WeatherOverride` rows take precedence as `manual`; remaining stations use `seasonal_averages.json` for the current month).
  2. `Warehouse` and `Shelter` records, each enriched with nearest-station flood risk.
  3. Unresolved `Incident` records (`status != "resolved"`): fire outbreaks are scored via `Incident.get_fire_assessment()` (`fire_incidents`), while reported non-fire emergencies (Flood, Cyclone, Waterlogging, Earthquake, etc.) render on the `"Other emergencies"` layer (`other_incidents`).
* `/map/weather/` lets Admins and Coordinators set/update per-station overrides (`update_or_create`) or reset any station back to its seasonal baseline. Changes broadcast over `/ws/alerts/` so open maps refresh automatically.

## Regenerating data

Seasonal averages (needs the original CSV, which is not committed): download the *"Flood Prediction by Noushin Gauhar"* dataset from Kaggle, then run:

```bash
python -c "from prediction.seasonal_averages import generate_seasonal_averages as g; g('path/to/FloodPrediction.csv')"
```

To retrain the model, run `model_training.ipynb` and replace `flood_prediction_pipeline.joblib` in the same Python/scikit-learn environment described in `requirements.txt`.

## Limitations & Scope

* **Flood model dataset bias:** `FloodPrediction.csv` is heavily imbalanced (~92% flood rows in labeled records), so the classifier mostly behaves as a wet-season detector rather than a real-time river-gauge forecast.
* **Seasonal baselines vs. live telemetry:** Unoverridden stations use historical monthly averages (`seasonal_averages.json`) unless an Admin/Coordinator enters a `WeatherOverride`.
* **Coarse spatial approximation:** Nearest-station lookup (`stations.py`) uses Euclidean distance on lat/lon coordinates rather than Haversine distance, river basin boundaries, or terrain elevation.
* **Fire score is rule-based:** No suitable labeled dataset exists for this combination of urban structural inputs; weights in `fire_severity.py` are documented heuristic judgment calls.
* **Out-of-scope hazard ML:** Cyclone track forecasting, river erosion prediction (which would require multi-temporal Landsat/Sentinel-2 satellite imagery or BWDB/CEGIS cross-section data), and landslide ML prediction are intentionally omitted; those disasters are supported purely as manually reported incidents plotted on `/map/`.
* **Basemap tiles require internet:** Leaflet JS/CSS is vendored locally, but Esri WorldStreetMap raster tiles load online.
