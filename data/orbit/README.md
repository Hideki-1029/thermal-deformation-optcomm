# Orbit data for TLE vs GNSS/POD studies

## Sentinel-1 AUX_POEORB (GNSS POD truth)

Public precise orbit files are hosted on AWS without authentication:

- Registry: [Sentinel-1 POD Products on AWS](https://registry.opendata.aws/s1-orbits/)
- Bucket: `s1-orbits`
- Prefixes: `AUX_POEORB/` (precise), `AUX_RESORB/` (restituted)

This repository downloads POEORB files over HTTPS. AWS CLI is optional:

```bash
aws s3 ls --no-sign-request s3://s1-orbits/AUX_POEORB/
aws s3 cp --no-sign-request s3://s1-orbits/AUX_POEORB/<file>.EOF .
```

Python entry point:

```powershell
python src/orbit/run_orbit_prediction_error.py
```

Downloaded files are cached under `data/orbit/sentinel1/`.

## TLE / GP history

Preferred source: Space-Track-style GP history parquet filtered by NORAD ID.

Default path:

```text
data/orbit/tle/tle_2026.parquet
```

This file is **not in git** (~480 MB). Download once per machine from HuggingFace:

- Dataset: [juliensimon/space-track-tle-history](https://huggingface.co/datasets/juliensimon/space-track-tle-history)
- Direct file: `data/tle_2026.parquet` in that dataset

From the repository root:

```powershell
mkdir data\orbit\tle
curl -L -o data\orbit\tle\tle_2026.parquet "https://huggingface.co/datasets/juliensimon/space-track-tle-history/resolve/main/data/tle_2026.parquet"
```

Python alternative:

```powershell
python -c "import urllib.request; from pathlib import Path; p=Path('data/orbit/tle/tle_2026.parquet'); p.parent.mkdir(parents=True, exist_ok=True); urllib.request.urlretrieve('https://huggingface.co/datasets/juliensimon/space-track-tle-history/resolve/main/data/tle_2026.parquet', p); print(p.stat().st_size)"
```

Requires `pyarrow` (see `requirements.txt`). The loader filters by NORAD ID at read time, so the full-year parquet is fine even when only Sentinel-1A (39634) is used.

Alternative: plain-text TLE history from
[CelesTrak Special Data Request (GP)](https://celestrak.org/NORAD/archives/request.php)

Set `satellite.gp_history_parquet` in `src/orbit/orbit_prediction_error_config.yaml`
when using a different local path.

## Notes

- Baseline compares **forward SGP4** from the latest GP/TLE with `epoch <= evaluation time`.
- Do **not** propagate a future TLE backward to past POD samples.
- Sentinel-1 AUX_POEORB is treated as truth (typical accuracy < 1 cm 3D).
- TLE/SGP4 error is mapped to ISL LOS angle assuming an 800 km partner range.
- Research policy: `docs/research_notes/memo_in_repository.md` section「軌道予測誤差との分離」.
- GNSS-grade (RESORB vs POEORB): `docs/research_notes/260811_gnss_optical_comm_orbit_error.md`
  - Runner: `python src/orbit/run_orbit_prediction_error_resorb.py`
  - Outputs: `results/orbit/sentinel1_resorb_vs_pod/`
  - PAT: `--config src/pat_acquisition/configs/pat_femap_los_config_resorb.yaml`
