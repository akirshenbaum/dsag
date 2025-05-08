import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import os
import glob

st.set_page_config(
    page_title="SAP BTP Cost Analysis Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- SAP BTP-inspired CSS ---
st.markdown("""
<style>
body, .stApp {
    background-color: #fff;
    font-family: '72', Arial, Segoe UI, sans-serif;
}
.stButton>button {
    background-color: #0a6ed1;
    color: white;
    border-radius: 4px;
    font-weight: bold;
    border: none;
    padding: 0.5em 1.5em;
}
.stSidebar {
    background-color: #f7f7f7;
}
h1, h2, h3, h4 {
    color: #32363a;
    font-weight: bold;
}
.stDataFrame, .stTable {
    background-color: #fff;
    border-radius: 8px;
    border: 1px solid #e5e5e5;
}
</style>
""", unsafe_allow_html=True)

# (Optional) SAP logo at the top of the sidebar
st.sidebar.image("https://www.sap.com/dam/application/shared/logos/sap-logo-svg.svg", width=120)

# --- SAP BTP Plotly Layout ---
plotly_layout = dict(
    font=dict(family="72, Arial, Segoe UI, sans-serif", size=14, color="#32363a"),
    plot_bgcolor="#fff",
    paper_bgcolor="#fff",
    title_font=dict(size=20, color="#0a6ed1"),
    legend=dict(bgcolor="#fff", bordercolor="#e5e5e5"),
)

# --- File Upload Section ---
st.sidebar.header("Upload Excel File")
SAMPLE_FILE = 'sample_data.xlsx'  # Use this as the sample data file

# Use a unique key for the file uploader to force reset
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

def reset_to_sample():
    st.session_state['uploader_key'] += 1
    st.session_state['uploaded_file'] = None
    st.rerun()

st.sidebar.button("Reset to Sample Data", on_click=reset_to_sample)

uploaded_file = st.sidebar.file_uploader(
    "Upload an Excel file", type=["xlsx", "xls"], key=f"file_uploader_{st.session_state['uploader_key']}"
)

# --- Sidebar Instructions (moved here) ---
with st.sidebar.expander("How to download cost data from SAP BTP Cockpit?"):
    st.markdown('''
    1. Log in to your SAP BTP Cockpit.
    2. Navigate to your Global Account.
    3. Go to the **Cost & Usage** section.
    4. Select the desired time period and filters.
    5. Click on **Export** or **Download** to get the Excel file.
    6. Save the file and upload it here using the uploader above.
    
    _For best results, use the default export format and do not modify the file structure._
    ''')

if uploaded_file is not None:
    excel_path = uploaded_file
    excel_engine = 'openpyxl'
    uploaded_file.seek(0)
else:
    if os.path.exists(SAMPLE_FILE):
        excel_path = SAMPLE_FILE
        excel_engine = 'openpyxl'
        st.info("Using sample data. Upload a file to analyze your own data.")
    else:
        st.warning("Please upload an Excel file or place 'GA export.xlsx' in the folder to begin analysis.")
        st.stop()

try:
    with pd.ExcelFile(excel_path, engine=excel_engine) as xls:
        quota_raw = pd.read_excel(xls, 0, skiprows=16, usecols=[0,1,2], header=None)
        quota_raw = quota_raw.dropna(subset=[0])
        quota_raw.columns = ['Quota Col 1', 'Quota Col 2', 'Quota Col 3']
        # Ensure all quota columns are string for display compatibility
        quota_raw = quota_raw.astype(str)
        df_main = pd.read_excel(xls, 2)
        # Get the last sheet name
        last_sheet_name = xls.sheet_names[-1]
        df_labels = pd.read_excel(xls, last_sheet_name)
except Exception as e:
    st.error(f"Could not read the Excel file. Please check the file format. Error: {e}")
    st.stop()

# --- Data Preparation ---
# Join main and label sheets robustly, using the third column of the last sheet as the label
if 'Subaccount ID' in df_main.columns and 'Subaccount ID' in df_labels.columns:
    df_main['Subaccount ID'] = df_main['Subaccount ID'].astype(str)
    df_labels['Subaccount ID'] = df_labels['Subaccount ID'].astype(str)
    # Use 'Key' and 'Value' columns for label
    key_col = df_labels.columns[1]
    value_col = df_labels.columns[2]
    df_labels['Label_Display'] = df_labels[key_col].astype(str) + ': ' + df_labels[value_col].astype(str)
    df_labels = df_labels[['Subaccount ID', 'Label_Display']]
    df_main = df_main.merge(df_labels, on='Subaccount ID', how='left')

for col in ['Start Date', 'End Date']:
    if col in df_main.columns:
        df_main[col] = pd.to_datetime(df_main[col], errors='coerce')
if 'Subaccount Name' in df_main.columns:
    df_main['Subaccount Name'] = df_main['Subaccount Name'].astype(str).fillna('Unknown')
if 'Service Name' in df_main.columns:
    df_main['Service Name'] = df_main['Service Name'].astype(str).fillna('Unknown')

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Exclude subaccounts
all_subaccounts = sorted(df_main['Subaccount Name'].astype(str).unique())
exclude_subaccounts = st.sidebar.multiselect(
    "Exclude Subaccounts",
    options=all_subaccounts,
    help="Select subaccounts to exclude from all analysis",
    key="exclude_subaccounts"
)

# Exclude directories (if available)
directory_col = None
for col in df_main.columns:
    if 'directory' in col.lower():
        directory_col = col
        break
if directory_col:
    all_directories = sorted(df_main[directory_col].astype(str).unique())
    exclude_directories = st.sidebar.multiselect(
        "Exclude Directories",
        options=all_directories,
        help="Select directories to exclude from all analysis",
        key="exclude_directories"
    )
else:
    exclude_directories = []

# Date selection options
date_option = st.sidebar.radio(
    "Select Date Range Type",
    ["Last Month", "Custom Range", "Last 3 Months", "Last 6 Months", "Last Year"]
)
if date_option == "Custom Range":
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(df_main['Start Date'].min(), df_main['Start Date'].max()),
        min_value=df_main['Start Date'].min(),
        max_value=df_main['Start Date'].max()
    )
    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1])
else:
    end_date = pd.Timestamp(df_main['Start Date'].max())
    if date_option == "Last Month":
        start_date = end_date - pd.DateOffset(months=1)
    elif date_option == "Last 3 Months":
        start_date = end_date - pd.DateOffset(months=3)
    elif date_option == "Last 6 Months":
        start_date = end_date - pd.DateOffset(months=6)
    else:
        start_date = end_date - pd.DateOffset(years=1)

filtered_df = df_main[(df_main['Start Date'] >= start_date) & (df_main['Start Date'] <= end_date)]

# Apply exclusion filters to filtered_df
if exclude_subaccounts:
    filtered_df = filtered_df[~filtered_df['Subaccount Name'].astype(str).isin(exclude_subaccounts)]
if directory_col and exclude_directories:
    filtered_df = filtered_df[~filtered_df[directory_col].astype(str).isin(exclude_directories)]

# Subaccount filter (mutually exclusive logic)
all_subaccounts_select = ['All'] + [s for s in all_subaccounts if s not in exclude_subaccounts]
selected_subaccount = st.sidebar.selectbox("Select Subaccount", all_subaccounts_select, key="select_subaccount")
if selected_subaccount != 'All':
    filtered_df = filtered_df[filtered_df['Subaccount Name'].astype(str) == selected_subaccount]

# Service filter
all_services = ['All'] + sorted(filtered_df['Service Name'].astype(str).unique())
selected_service = st.sidebar.selectbox("Select Service", all_services, key="select_service")
if selected_service != 'All':
    filtered_df = filtered_df[filtered_df['Service Name'].astype(str) == selected_service]

# --- Key Metrics ---
st.markdown(f"""
# 📊 SAP BTP Cost Analysis Dashboard
### Period: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}
""")

total_cost = filtered_df['Cost'].sum() if 'Cost' in filtered_df.columns else 0
nonzero_costs = filtered_df[filtered_df['Cost'] > 0]['Cost'] if 'Cost' in filtered_df.columns else pd.Series([])
avg_cost_nonzero = nonzero_costs.mean() if not nonzero_costs.empty else 0
median_cost = filtered_df['Cost'].median() if 'Cost' in filtered_df.columns and not filtered_df.empty else 0
total_usage = filtered_df['Usage'].sum() if 'Usage' in filtered_df.columns else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Cost", f"${total_cost:,.2f}")
col2.metric("Avg Cost (nonzero)", f"${avg_cost_nonzero:,.2f}")
col3.metric("Median Cost", f"${median_cost:,.2f}")
st.caption("Avg Cost (nonzero): Average cost per record, excluding zero-cost rows. Median Cost: The middle value of all costs, less sensitive to outliers and zeros.")

# --- Top Subaccounts by Cost ---
st.subheader("🏆 Top Subaccounts by Cost")
if 'Subaccount Name' in filtered_df.columns and 'Cost' in filtered_df.columns:
    subaccount_costs = filtered_df.groupby('Subaccount Name')['Cost'].sum().reset_index().sort_values('Cost', ascending=False).head(10)
    fig1 = px.bar(subaccount_costs, x='Subaccount Name', y='Cost', title='Top 10 Subaccounts by Cost', color='Cost', color_continuous_scale='Viridis')
    fig1.update_layout(**plotly_layout)
    st.plotly_chart(fig1, use_container_width=True)

# --- Top Services by Cost ---
st.subheader("🔧 Top Services by Cost")
if 'Service Name' in filtered_df.columns and 'Cost' in filtered_df.columns:
    service_costs = filtered_df.groupby('Service Name')['Cost'].sum().reset_index().sort_values('Cost', ascending=False).head(10)
    fig2 = px.bar(service_costs, x='Service Name', y='Cost', title='Top 10 Services by Cost', color='Cost', color_continuous_scale='Viridis')
    fig2.update_layout(**plotly_layout)
    st.plotly_chart(fig2, use_container_width=True)

# --- Anomaly Detection ---
st.subheader("⚠️ Cost Anomalies")
st.markdown('''
**What is a Cost Anomaly?**

This chart highlights services whose costs are unusually high compared to their typical (average) monthly cost. We use a statistical method called the "z-score" to measure how much a service's cost in the selected period deviates from its average. A high z-score means the cost is much higher than usual, which could indicate unexpected usage, a pricing change, or a potential issue worth investigating.

**How to use this chart:**
- Bars further to the right (higher z-score) are more "anomalous."
- Review these services to understand why their costs spiked.
- This can help you catch mistakes, unexpected growth, or opportunities for optimization.
''')
def detect_anomalies(df, group_col, value_col, n=5):
    # Only keep groups with more than one record
    counts = df.groupby(group_col)[value_col].count().reset_index()
    valid_groups = counts[counts[value_col] > 1][group_col]
    df_valid = df[df[group_col].isin(valid_groups)]
    if df_valid.empty:
        return pd.DataFrame()
    grouped = df_valid.groupby(group_col)[value_col].agg(['mean', 'std']).reset_index()
    df_with_stats = df_valid.merge(grouped, on=group_col)
    # Avoid division by zero
    df_with_stats['z_score'] = (df_with_stats[value_col] - df_with_stats['mean']) / df_with_stats['std'].replace(0, np.nan)
    df_with_stats = df_with_stats.replace([np.inf, -np.inf], np.nan).dropna(subset=['z_score'])
    return df_with_stats.nlargest(n, 'z_score')

if 'Service Name' in filtered_df.columns and 'Cost' in filtered_df.columns:
    anomalies = detect_anomalies(filtered_df, 'Service Name', 'Cost')
    if anomalies.empty:
        st.info('Not enough data for meaningful anomaly detection (need at least two records per service).')
    else:
        anomaly_fig = px.bar(anomalies, x='Service Name', y='Cost', title='Top 5 Cost Anomalies', labels={'Cost': 'Cost (USD)', 'Service Name': 'Service'}, color='z_score', color_continuous_scale='Reds')
        anomaly_fig.update_layout(**plotly_layout)
        st.plotly_chart(anomaly_fig, use_container_width=True)

# --- Trend Analysis ---
st.subheader("📈 Cost Trend")
if 'Start Date' in filtered_df.columns and 'Cost' in filtered_df.columns:
    monthly_costs = filtered_df.groupby('Start Date')['Cost'].sum().reset_index()
    fig3 = px.line(monthly_costs, x='Start Date', y='Cost', title='Cost Trend Over Time', labels={'Cost': 'Cost (USD)', 'Start Date': 'Date'})
    fig3.update_layout(**plotly_layout)
    st.plotly_chart(fig3, use_container_width=True)

# --- Label Analysis (appended, not a filter) ---
if 'Subaccount ID' in df_main.columns and 'Subaccount ID' in df_labels.columns:
    label_col_name = 'Label_Display'
    label_df = df_main[[label_col_name, 'Cost', 'Usage']].copy() if 'Usage' in df_main.columns else df_main[[label_col_name, 'Cost']].copy()
    label_df = label_df.dropna(subset=[label_col_name])
    st.subheader(f"🏷️ Label Analysis: {label_col_name}")
    # Bar chart: Top labels by cost
    label_costs = label_df.groupby(label_col_name)['Cost'].sum().reset_index().sort_values('Cost', ascending=False)
    fig_label = px.bar(label_costs.head(10), x=label_col_name, y='Cost', title=f'Top 10 Labels by Cost', color='Cost', color_continuous_scale='Viridis')
    fig_label.update_layout(**plotly_layout)
    st.plotly_chart(fig_label, use_container_width=True)
    # Pie chart: Cost distribution by label (top 8 + Other)
    top_n = 8
    label_costs_sorted = label_costs.sort_values('Cost', ascending=False)
    if len(label_costs_sorted) > top_n:
        top_labels = label_costs_sorted.head(top_n)
        other_sum = label_costs_sorted['Cost'][top_n:].sum()
        import pandas as pd  # already imported, but safe to repeat
        other_row = pd.DataFrame([{label_col_name: 'Other', 'Cost': other_sum}])
        pie_data = pd.concat([top_labels, other_row], ignore_index=True)
    else:
        pie_data = label_costs_sorted
    fig_label_pie = px.pie(pie_data, values='Cost', names=label_col_name, title=f'Cost Distribution by Label')
    fig_label_pie.update_layout(**plotly_layout)
    st.plotly_chart(fig_label_pie, use_container_width=True)
    # Table: Cost and usage by label
    if 'Usage' in label_df.columns:
        label_usage = label_df.groupby(label_col_name)['Usage'].sum().reset_index().sort_values('Usage', ascending=False)
        st.dataframe(label_usage.style.format({'Usage': '{:,.2f}'}))
    st.dataframe(label_costs.style.format({'Cost': '${:,.2f}'}))
else:
    st.info("No label data available for analysis.")

# --- Quota Usage Overview ---
st.subheader("📏 Quota Usage Overview")
if not quota_raw.empty:
    # Clean and convert columns
    quota_viz = quota_raw.copy()
    quota_viz['Date'] = pd.to_datetime(quota_viz['Quota Col 1'], errors='coerce')
    quota_viz['Usage (%)'] = pd.to_numeric(quota_viz['Quota Col 2'], errors='coerce')
    quota_viz['Type'] = quota_viz['Quota Col 3'].astype(str)
    quota_viz = quota_viz.dropna(subset=['Date', 'Usage (%)'])
    quota_viz = quota_viz.sort_values('Date')
    quota_viz['Over Quota'] = quota_viz['Usage (%)'] >= 100

    # Plot
    fig_quota = go.Figure()
    fig_quota.add_trace(go.Bar(
        x=quota_viz['Date'],
        y=quota_viz['Usage (%)'],
        marker_color=["crimson" if over else "#636EFA" for over in quota_viz['Over Quota']],
        name='Usage (%)',
        hovertext=quota_viz['Type']
    ))
    fig_quota.add_trace(go.Scatter(
        x=quota_viz['Date'],
        y=[100]*len(quota_viz),
        mode='lines',
        line=dict(color='green', dash='dash'),
        name='Quota (100%)'
    ))
    fig_quota.update_layout(
        title='Monthly Usage as % of Quota',
        xaxis_title='Date',
        yaxis_title='Usage (%)',
        showlegend=True,
        height=400
    )
    fig_quota.update_layout(**plotly_layout)
    st.plotly_chart(fig_quota, use_container_width=True)
    
    # Table of months at or above quota
    if quota_viz['Over Quota'].any():
        st.warning('Some months are at or above quota!')
        st.dataframe(quota_viz[quota_viz['Over Quota']][['Date', 'Usage (%)', 'Type']])
    else:
        st.success('All months are within quota.')
    
    # Show raw quota table
    with st.expander("View Raw Quota Table"):
        st.dataframe(quota_raw)
else:
    st.info("No quota information found in the first sheet of the Excel file.")

# --- Raw Data View ---
with st.expander("📋 View Raw Data"):
    st.dataframe(filtered_df)

# Add disclaimer at the bottom of the sidebar
st.sidebar.markdown(
    """
    <div style='font-size: 0.8em; color: #888; margin-top: 2em;'>
    <strong>Disclaimer:</strong> All financial data and analysis shown here are for product feedback purposes only. The numbers may be inaccurate or misleading and should not be relied upon for any financial decisions. Do not trust these results. No warranty is provided.
    </div>
    """,
    unsafe_allow_html=True
) 