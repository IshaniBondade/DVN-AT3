# AI Provenance Matrix

The below table records how our group used generative AI tools during the project. It also explains how we checked the results to make sure they were correct.

| Artefact | Who | Tool | What was asked | What came back | How it was verified | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `app.py`, `common.py`, `tabs/overview.py`, `scripts/make_processed.py` | Ishani Bondade | Claude and Gemini | Help with the Streamlit app layout, Overview chart and Python data cleaning script. | Initial app structure, chart code and a script to clean and group organisation names. | Checked the total of 1,078 models and manually verified Google (155) + DeepMind (38) = 193. Also re-ran the cleaning script and checked the final data. | Used after correcting a missing Google Cloud name and adjusting the chart labels and layout. |
| `tabs/compute.py` | Harshini Mitra |
| `tabs/geography.py` | Biplav Adhikari |
| `tabs/organisations.py` | Hoang Khai Nguyen |