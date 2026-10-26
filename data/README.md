# Source data and provenance

## Epoch AI

- Dataset: Notable AI models, from [Epoch AI](https://epoch.ai/data/ai-models).
- Download: <https://epoch.ai/data/notable_ai_models.csv>.
- Snapshot date: 26 October 2026.
- Raw file: `raw/notable_ai_models.csv`; unchanged source bytes.
- Source licence: CC BY 4.0. Attribution: Epoch AI, Notable AI Models database.
- Raw SHA-256: `dcd97028735d9d985b3ffab6bb19e0e711b400c5c513a4c8dc4acf7fe6a728f5`.
- Raw rows: 1,082; raw columns: 47.

The processed file selects the model, developer, publication date, country, domain, task and link fields. It adds a stable record ID derived from the model name, organisation and date, plus the source record's 1-based ordinal. A source record ordinal is not a physical text-file line number because CSV fields may contain newlines.

Run `python -m src.pipeline build` from the feature root to reproduce it. This changes the processed file and validation report, not the raw snapshot. The app never silently fetches a newer dataset.

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
