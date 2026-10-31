# prediction

Flood-risk prediction, fire-escalation scoring, and the map data and prototype for CrisisNet. Nothing in this folder depends on Django, so every module can be tested on its own.

## Setup

Python 3.10 or newer is required.

```
pip install -r prediction/requirements.txt
```

The versions in `requirements.txt` are pinned on purpose. `flood_prediction_pipeline.joblib` is a pickled scikit-learn pipeline, and it only loads cleanly on the scikit-learn version it was trained with. Only load `.joblib` files that came from this repository, since pickle files can run code when loaded.

All commands below are run from the folder that contains `manage.py`, using `python -m`, because the modules use relative imports.

## What is here

| File | Purpose |
|---|---|
| `flood_model.py` | `predict_flood_risk()`: flood risk from weather values |
| `fire_severity.py` | `calculate_fire_severity()`: rule-based fire escalation score |
| `stations.py` | The 33 weather stations (name, lat, lon) and nearest-station lookup |
| `seasonal_averages.py` | Per-station, per-month historical weather averages, used as the default input |
| `seasonal_averages.json` | Generated output of the above, committed so nothing needs the full dataset at runtime |
| `assemble_map_data.py` | Combines flood predictions into the JSON payload the map consumes |
| `generate_sample_payload.py` | Builds a sample payload (real flood layer, fake fire incidents, shelters and warehouses) |
| `map_prototype/` | Standalone Leaflet map that reads the payload |
| `model_training.ipynb` | How the flood model was trained and evaluated |
| `flood_prediction_pipeline.joblib` | The trained model |

## Using the modules

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

Impossible values (negative rainfall, humidity above 100, missing or non-numeric input) raise `ValueError`. Catch it in your view. Values that are possible but outside the training range still produce a prediction, with a `warnings` list added to the result.

`flood_probability` is the probability of the flood class and is the better value to use for colors or sorting. `confidence` is only the probability of whichever class won.

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
| `material` | `tin`, `wood`, `bamboo` count as combustible; anything else (for example `concrete`) does not |
| `road_access` | `narrow_alley`, `medium_road`, `wide_road` |
| `density` | `slum`, `high_density` count as dense; for example `residential`, `low_density` do not |
| `time_of_day` | Integer hour, 0 to 23 |
| `occupancy_type` | `chemical`, `garment_factory`, `mall`, `industrial`, `residential`, `other` (default) |

A chemical facility is always rated High, whatever the other inputs are. When that rule raised the label, `floor_applied` is `True`. `factors` shows how many points each input contributed, so a dashboard can explain a rating. An invalid hour or an unknown `occupancy_type` raises `ValueError`.

### Map payload

```python
payload = build_map_payload(
    manual_entries={"Rajshahi": {"rainfall": 600, "relative_humidity": 85, "cloud_coverage": 6.5}},
    fire_incidents=[...],   # already scored, each with lat and lon added by the caller
    month=None,             # defaults to the current month
)
```

The payload has `generated_at`, `flood_risk_zones` and `fire_incidents`. Each flood entry has `data_source` set to `manual` or `seasonal_average`. For every station without a manual entry, the seasonal average for that month is used. A station with no data at all is left out rather than guessed. `get_shelter_flood_risk(lat, lon, zones)` returns the risk entry of the nearest station, so a shelter or warehouse can show its area's flood risk.

## Running the map prototype

```
python -m prediction.generate_sample_payload
cd prediction/map_prototype
python -m http.server 8000
```

Open http://localhost:8000. A local server is needed because browsers block `fetch()` for files opened directly. Pass a month number to the generator (for example `7`) to preview another season. Leaflet is bundled in `map_prototype/vendor/leaflet/`, so the page itself needs no internet. The basemap tiles still load from OpenStreetMap, which does need a connection.

## Regenerating data

Seasonal averages (needs the original CSV, which is not committed): download the "Flood Prediction by Noushin Gauhar" dataset from Kaggle, then:

```
python -c "from prediction.seasonal_averages import generate_seasonal_averages as g; g('path/to/FloodPrediction.csv')"
```

To retrain the model, run `model_training.ipynb` and replace `flood_prediction_pipeline.joblib`. Train in the same environment that `requirements.txt` describes.

## Limitations

- The flood model was trained on records from periods when floods were being tracked, so it behaves mostly as a wet-season detector. A High result means conditions resemble flood-season records, not that flooding is happening. It is a proof of concept, not a forecast.
- Seasonal-average predictions are an indicative baseline, not live conditions. Admin-entered values override them.
- The fire score is a weighted heuristic, not a trained model. No suitable labeled dataset exists for this combination of inputs. The weights are documented in `fire_severity.py` and are judgment calls.
