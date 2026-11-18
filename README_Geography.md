# Geography tab

## Overview and interactions

Explore where notable AI models are developed, compare country shares across five-year periods, and drill down into model details. The shared app passes filtered data through `app.py → tabs/geography.py → src/views.py`.

| View | What it does |
| --- | --- |
| World map | Shows country shares for the selected period, with values available below the map. |
| Country tables | Show the five leading origins or up to four selected countries. **All map values** opens the full list. |
| Shares over time | Compares the three leading countries from 2021–2025, or selected countries, across three periods. **Other origins** contains the remaining share. Click a column to change period. |
| AI types and model details | Select an AI type, then click a country bar to inspect models and download their records. |
| Accessibility | Compares country counts by weight status. Expand **Accessibility and counting** for global metrics, detailed categories and the counting note. |

## Country shares and model credits

The tab uses every affiliation in `country_raw`, normalises country aliases and removes duplicate country tags within each record.

- **Credit per country per model = 1 ÷ number of distinct listed countries.** Country model credits sum these contributions.
- **Country share (%) = country model credits ÷ all models with known origins × 100**, within the same period and shared filters.
- For an AI-type share, both the credits and denominator use only models tagged with that type.

Missing origins are excluded from shares; **Multinational** remains in the totals. Associated-model counts count a joint model once in each listed country. AI types can overlap, and model versions remain separate records.

## Five-year periods and filters

The year is extracted from **Publication date**. **2011–2015, 2016–2020 and 2021–2025** include both boundary years. Each window pools its records; totals are neither cumulative nor averages of annual shares. The default is 2021–2025.

Shared **year, sector and frontier filters** apply throughout. The period selector controls the map, accessibility, types and details; the time chart compares all three windows. A narrower year filter can leave windows partial or empty.

Country selection changes displayed countries without changing the global denominator. The AI-type selector affects only the type chart and model details.

## Accessibility calculations

The tab checks **Open model weights?** first. If missing, **Model accessibility** labels identify open-weight releases; API, hosted, limited-access and unreleased labels count as not open weights. Unclear values remain **Unknown**.

**Open-weight share (%) = open-weight models ÷ all models listed for that country × 100.** The denominator includes unknown weight status. Each joint model counts once per listed country; global metrics count each model once.

Country coverage counts countries with at least one open-weight model, excluding missing origins and Multinational. Global metrics and category counts follow the period and shared filters, independently of country selection.

## Relevant Python files

| File | Role |
| --- | --- |
| `app.py`, `common.py` | Load shared processed data and apply dashboard filters. |
| `tabs/geography.py` | Adapt shared columns for Geography. |
| `src/views.py` | Render controls, tables, metrics and model details. |
| `src/data.py` | Calculate credits, shares, periods, type counts and accessibility. |
| `src/charts.py`, `src/map.py` | Build the charts and map. |
| `src/settings.py` | Read configuration and resolve data paths. |
| `scripts/make_processed.py` | Rebuild the shared processed CSV from raw data. |
| `src/pipeline.py` | Run preprocessing and write validation metadata. |

Run from the repository root using Python 3.11 or later:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Rebuild data and validation metadata with `python -m src.pipeline build`.
