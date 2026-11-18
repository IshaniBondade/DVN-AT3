# DVN-AT3
# Who Controls the AI Frontier?

## Research Question
**Is frontier AI development concentrating in fewer organisations, or spreading out?**

This question is arguable because the data supports two competing interpretations depending on the metric chosen: counting notable model releases suggests a broadening ecosystem with over 230 contributing institutions, whereas measuring total training compute reveals heavy oligopolistic concentration among a handful of frontier labs.

---

## Target Persona & Decision Context
* **Persona:** Elena Vance, Senior AI Policy Analyst at an international technology regulator.
* **Decision Served:** Determining whether regulatory intervention should prioritise **antitrust and compute-threshold oversight** (if frontier capability is locked inside a small oligopoly of mega-labs) or **public research infrastructure and open-ecosystem grants** (if meaningful frontier models are diffusing broadly across academia and smaller entrants).

---

## User Stories
1. **As a** Senior AI Policy Analyst, **I want to** compare the share of notable AI models released by top organisations against their share of total training compute, **so that** I can determine whether model volume masks underlying resource concentration.
2. **As a** Senior AI Policy Analyst, **I want to** filter AI model releases by publication year, organisational sector, and frontier compute thresholds, **so that** I can evaluate whether new entrants are breaking into the frontier tier or falling behind since 2020.
3. **As a** Senior AI Policy Analyst, **I want to** examine the geographic distribution of frontier AI development across countries and 5-year periods, **so that** I can identify regional concentration risks and dependencies in global AI governance.

---

## Repository Structure
* `app.py` — Main Streamlit entry point, global filters, empty-state guards, and narrative layout.
* `common.py` — Shared data loaders, constants, and colour-blind-safe palette.
* `theme.py` & `.streamlit/config.toml` — Dark UI styling and Okabe-Ito colour-vision-deficiency-safe palette.
* `tabs/` — Modular views for `overview.py`, `organisations.py`, `compute.py`, `geography.py`, and `methods.py`.
* `data/raw/` — Source Epoch AI CSV extract (`notable_ai_models.csv`) and licensing metadata (`EPOCH_README.md`).
* `data/processed/` — Cleaned analytical dataset (`models_clean.csv`).
* `data/DATA_DICTIONARY.md` — Full schema, source provenance, licence, and transform documentation.
* `scripts/make_processed.py` — Deterministic script that regenerates `models_clean.csv` from `data/raw/notable_ai_models.csv`.
* `AI_PROVENANCE.md` — Substantive AI usage log with verification checks across all group members.
* `DISCLOSURE.md` — Data provenance, analytical limitations, and AI disclosure statement.

---

## Geography tab

The group app passes the shared, filtered data through `app.py → tabs/geography.py → src/views.py`. The adapter preserves all developer-country affiliations from `country_raw`; `src/data.py` normalises country aliases, removes duplicate tags and calculates the Geography results.

### What the tab shows

| View | Purpose and interaction |
| :--- | :--- |
| World map | Country shares for the selected period, with readable values below. Country codes join the results to map boundaries; developer labels use single-country records. |
| Shares over time | Compares the three leading countries in 2021–2025, or selected countries, across all three periods. Remaining shares appear as **Other origins**. Click a column to change the selected period. |
| AI types | Select a type to see its country distribution; click a country bar to explore its models. Types can overlap. |
| Model details | Shows developers, dates, source origins, country credits and source links; records can be downloaded as CSV. |
| Open weights | Shows country coverage, accessibility counts and each country's open-weight share. |

### How country shares are calculated

Countries refer to the developing organisations listed in each model's dataset record. Each model counts once; that count is split equally across its distinct developer countries to give **model credits**. **Example:** a record listing USA and France contributes **0.5 to each**; a record listing only USA contributes **1 to USA**.

**Country share (%) = country model credits ÷ all known-origin models in the same period and shared filters × 100.**

For the AI-type chart, both parts of the calculation use only that type. Missing origins are excluded; **Multinational** remains in share totals. Associated-model counts count a joint model once for each country, so these counts differ from credits. Model versions remain separate records.

### Five-year periods and filters

- **2011–2015, 2016–2020 and 2021–2025** are separate, inclusive windows. They reduce annual noise in sparse early data, but hide changes within each period. Totals are not cumulative; the default view is 2021–2025.
- Shared **year, sector and Epoch frontier-flag filters** apply throughout. A narrow year range can leave a period partial or empty.
- The period selector controls the map, accessibility, types and details; the time chart compares all three periods.
- Selecting up to **four countries** changes what is displayed without recalculating the global share denominator. The type selector affects only the type chart and model details.

### Open-weight coverage

The tab checks Epoch's `Open model weights?` field first. If it is missing, it checks `Model accessibility`, which can also label a model as **Open weights**. API-only, hosted, limited-access and unreleased labels are counted as not open weights; unclear values remain **Unknown**. The tab shows country coverage, model counts and open-weight percentages using all models listed for each country. Country selection filters the table; headline totals follow the period and shared filters.

### Run and rebuild

Use Python 3.11 or later from the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

To regenerate the shared processed CSV and validation metadata:

```bash
python -m src.pipeline build
```
