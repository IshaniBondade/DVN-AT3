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

## Geography integration

This existing `geography` checkout uses branch `feature-geography`. The group app calls `tabs/geography.py`, which imports `src/views.py`. Keep the existing `src/` structure when merging this contribution. The other members' feature branches remain separate; their tabs on main are placeholders.

## Run locally

From this folder:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On this Mac the existing interpreter is:

```bash
/opt/anaconda3/bin/python3 -m streamlit run app.py
```

## Structure and connection

```text
geography/
├── app.py                 Group dashboard entry point and shared filters
├── common.py              Shared data loading
├── theme.py               Shared styling
├── tabs/
│   └── geography.py       render(df, df_all) adapter used by app.py
├── src/
│   ├── views.py           Geography interface
│   ├── data.py            Attribution and accessibility calculations
│   ├── charts.py          Geography charts
│   └── map.py             World map renderer
├── scripts/
│   └── make_processed.py  Shared-format processed data builder
├── data/                  Agreed shared source snapshot and map assets
├── config.toml            Geography periods and defaults
├── dashboard.yml          Geography display text
├── requirements.txt
└── tests/
```

The connection is `app.py → tabs/geography.py → src/views.py`. There is no separate features directory in this working folder. The template's other feature tabs are placeholders.

Shared year, sector and frontier filters apply to Geography. Five-year windows further filter the results; selecting a narrow year range can make a period partial or empty. Country selections affect display only. Country shares split joint models equally among their distinct source origins. Open-weight coverage describes developer origins, not geographic user access rights.

## Data and checks

The raw CSV is main's agreed 19 October 2026 snapshot: 1,078 records and 47 columns. The processed CSV is regenerated from it with 20 columns; the 15 shared columns retain main's definitions and five extra fields support Geography. The shared processed format preserves original country and organisation tags, model accessibility, weights flags, source links, tasks and source row numbers. The organisation overview continues to use the template's first-listed organisation method; Geography uses fractional country attribution.

```bash
python -m src.pipeline build
python -m pytest -q
```


## Dependencies

`requirements.txt` keeps main's Streamlit, pandas and Altair requirements and adds Plotly and PyYAML, which Geography imports. Install the complete file to run every included tab. Tests are in `requirements-dev.txt`. Python 3.11 or later is required for `tomllib`.

## Publishing

This is a local integration. Include the source files, shared shell and documentation together in the Geography branch when preparing a later pull request. Running Streamlit does not push changes.
