# SAP BTP Cost Analysis Dashboard

This dashboard allows you to analyze SAP BTP cost and usage data from Excel exports. It features interactive charts, label analysis, quota usage, and more, with a SAP-inspired look and feel.

## Features
- Upload your own Excel export or use the provided sample file
- Filter by date, subaccount, and service
- Analyze costs by subaccount, service, and custom labels
- Detect cost anomalies and trends
- Visualize quota usage
- SAP BTP-inspired UI and charts

## Requirements
- Python 3.8 or higher
- pip (Python package manager)

## Installation
1. **Clone or download this repository** to your local machine.
2. (Optional but recommended) **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. **Place your Excel export file** (e.g., `GA export.xlsx`) in the project folder, or use the sample file provided.
2. **Run the Streamlit app**:
   ```bash
   streamlit run app.py
   ```
3. **Open your browser** to the local URL shown in the terminal (usually http://localhost:8501).
4. **Upload your Excel file** or use the sample data. Use the sidebar to filter and explore the data.

## Notes
- All data and analysis are for product feedback purposes only. Results may be inaccurate and should not be relied upon for financial decisions.
- For best results, use Excel files with the same structure as the provided sample.
- If you encounter errors, check that your Python version and packages match the requirements.

## Troubleshooting
- If you see errors about `set_page_config`, make sure no Streamlit commands come before `st.set_page_config()` in `app.py`.
- For date parsing warnings, ensure your Excel date columns are formatted consistently.
- For ArrowTypeError warnings, the app will attempt to auto-fix column types, but you may need to check your data.

## License
This project is for demonstration and feedback purposes only. No warranty is provided. 