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

## Running Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```