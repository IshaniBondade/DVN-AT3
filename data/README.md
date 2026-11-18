# Source data and provenance

## Epoch AI

- Dataset: Notable AI models, from [Epoch AI](https://epoch.ai/data/ai-models).
- Download: <https://epoch.ai/data/notable_ai_models.csv>.
- Snapshot date: 19 October 2026, matching the group's `main` branch.
- Raw file: `raw/notable_ai_models.csv`; unchanged source bytes.
- Source licence: CC BY 4.0. Attribution: Epoch AI, Notable AI Models database.
- Raw SHA-256: `3ef26619430a93ee4d126bc46e91699fe6f2b15ea7b8e830f0a565e32caaa224`.
- Raw rows: 1,078; raw columns: 47.

The shared processed file contains 1,078 records and 20 columns. It retains main's 15 fields and common cleaning rules, plus `country_raw`, `task`, `link`, `open_model_weights` and `source_record`. The source record is the raw record's 1-based ordinal, not a physical text-file line number because CSV fields may contain newlines. Geography creates its stable hashed record ID and fractional country credits in memory; those are not additional columns in the saved CSV. See `DATA_DICTIONARY.md` for all 20 saved fields and the subsequent transformations.

Run `python -m src.pipeline build` from this repository root to reproduce it. This runs the existing `scripts/make_processed.py` and refreshes the processed file, source metadata and validation report, including both file hashes. It does not change the raw snapshot. The app never silently fetches a newer dataset. There is one active raw model CSV and one processed model CSV; the geometry files are separate map support assets.

The 2011–2025 comparison contains 858 model records, including one without an origin. The 2021–2025 period contains 494 records with known origins and 18 AI-type tags. No demo values are invented.

## Geography

- Published atlas: [`@d3-maps/atlas` 1.0.0](https://github.com/souljorje/d3-maps/tree/main/packages/atlas).
- Original module: <https://esm.sh/@d3-maps/atlas@1.0.0/world/countries/countries-110m>.
- Geometry was converted from its `objects.features` TopoJSON using `topojson-client` 3.1.0, Antarctica omitted and coordinates rounded to two decimals for a compact world view.
- `geo/world.geojson` contains the converted published geometry. `feature.properties.id` is the ISO3 join key; it is not a numeric country code.
- `geo/country_codes.json` maps dataset country/region labels to those keys. Unmapped or too-small territories remain in aggregates and are explicitly noted in the app.
- The atlas package declares an MIT licence; its notice is included as `geo/ATLAS-LICENSE`.
- Projection: D3 Natural Earth 1, fitted to the map's actual width and height.

Boundaries are geographic display context. Source region labels are retained and should not be interpreted as a statement about sovereignty.
