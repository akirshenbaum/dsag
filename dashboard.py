import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import plotly.io as pio

# Read the CSV file
df = pd.read_csv('GA export.csv')

# Convert date columns to datetime
df['Start Date'] = pd.to_datetime(df['Start Date'])
df['End Date'] = pd.to_datetime(df['End Date'])

# Get the most recent month's data
latest_month = df['Start Date'].max()
latest_data = df[df['Start Date'] == latest_month]

# Calculate total cost per subaccount for the latest month
subaccount_costs = latest_data.groupby('Subaccount Name')['Cost'].sum().reset_index()
subaccount_costs = subaccount_costs.sort_values('Cost', ascending=False)

# Get top 5 subaccounts
top_5_sas = subaccount_costs.head(5)

# Create a bar chart for top 5 SAs
fig = px.bar(top_5_sas, 
             x='Subaccount Name', 
             y='Cost',
             title='Top 5 Subaccounts by Cost (Latest Month)',
             labels={'Cost': 'Cost (USD)', 'Subaccount Name': 'Subaccount'},
             color='Cost',
             color_continuous_scale='Viridis')

# Update layout
fig.update_layout(
    xaxis_tickangle=-45,
    yaxis_title='Cost (USD)',
    showlegend=False,
    height=600
)

# Save the figure as HTML
pio.write_html(fig, 'top_5_sas_dashboard.html')

# Create a detailed breakdown of services for top 5 SAs
service_breakdown = latest_data[latest_data['Subaccount Name'].isin(top_5_sas['Subaccount Name'])]
service_costs = service_breakdown.groupby(['Subaccount Name', 'Service Name'])['Cost'].sum().reset_index()

# Create a stacked bar chart for service breakdown
fig2 = px.bar(service_costs,
              x='Subaccount Name',
              y='Cost',
              color='Service Name',
              title='Service Cost Breakdown for Top 5 Subaccounts',
              labels={'Cost': 'Cost (USD)', 'Subaccount Name': 'Subaccount'},
              barmode='stack')

# Update layout
fig2.update_layout(
    xaxis_tickangle=-45,
    yaxis_title='Cost (USD)',
    height=600
)

# Save the service breakdown figure
pio.write_html(fig2, 'service_breakdown_dashboard.html')

# Print summary statistics
print("\nTop 5 Subaccounts Summary:")
print("==========================")
for _, row in top_5_sas.iterrows():
    print(f"\n{row['Subaccount Name']}:")
    print(f"Total Cost: ${row['Cost']:,.2f}")
    
    # Get service breakdown for this subaccount
    sa_services = service_costs[service_costs['Subaccount Name'] == row['Subaccount Name']]
    print("\nService Breakdown:")
    for _, service in sa_services.iterrows():
        print(f"- {service['Service Name']}: ${service['Cost']:,.2f}") 