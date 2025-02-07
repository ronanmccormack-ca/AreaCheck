# Import necessary libraries
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import requests
import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import numpy as np
from scipy.stats import gaussian_kde
import os


def has_from_civic_number(civic_number, std_street):
    base_url = 'https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/property-tax-report/records'
    params = {
        'where': f"to_civic_number='{civic_number}' AND street_name='{std_street}'",
        'limit': 100
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            df = pd.DataFrame(data['results'])
            if 'from_civic_number' in df.columns:
                return df['from_civic_number'].notnull().any()
    return False


def get_property_data(civic_number, std_street, from_civic_number=None):
    """
    Fetch property data for a specific civic number and street from Vancouver open data.

    Args:
        civic_number (str or int): The civic number to search for.
        std_street (str): The standard street name to search for.

    Returns:
        List[dict]: A list of dictionaries containing the filtered property data from the API call.
    """
    base_url = 'https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/property-tax-report/records'

    # If from_civic_number is provided, include it in the query
    if from_civic_number:
        params = {
            'where': f"to_civic_number='{civic_number}' AND from_civic_number='{from_civic_number}' AND street_name='{std_street}'",
            'order_by': 'report_year asc',
            'limit': 100
        }
    else:
        params = {
            'where': f"to_civic_number='{civic_number}' AND street_name='{std_street}'",
            'order_by': 'report_year asc',
            'limit': 100
        }

    # Make the request
    response = requests.get(base_url, params=params)

    # If the response is successful
    if response.status_code == 200:
        data = response.json()

        # Check if 'results' exists in the response
        if 'results' in data:
            results = data['results']

            # Keys to keep
            keys_to_keep = ["pid", "legal_type", 'land_coordinate', "zoning_district", "from_civic_number",
                            "to_civic_number", "street_name",
                            'current_land_value', 'current_improvement_value', 'previous_land_value',
                            'previous_improvement_value',
                            'year_built', 'tax_levy', 'neighbourhood_code', 'report_year']

            # Extract specific columns (keys) from the JSON response
            filtered_data = [{key: item.get(key) for key in keys_to_keep} for item in results]

            for item in filtered_data:
                current_land_value = item.get('current_land_value', 0)
                current_improvement_value = item.get('current_improvement_value', 0)
                previous_land_value = item.get('previous_land_value', 0)
                previous_improvement_value = item.get('previous_improvement_value', 0)

                item['total_value'] = current_land_value + current_improvement_value
                item['previous_value'] = previous_land_value + previous_improvement_value

                # Calculate value_change in percentage and round to 2 decimal places
                if item['previous_value'] > 0:
                    item['value_change'] = round(((item['total_value'] / item['previous_value']) - 1) * 100, 2)
                else:
                    item['value_change'] = None  # Set to None if no previous value for comparison

            # Return the filtered list of dictionaries with calculations
            return filtered_data
        else:
            return []  # Return an empty list if no 'results'
    else:
        return []  # Return an empty list on failure


def extract_last_land_coordinate(data_list):
    """
    Extract the 'land_coordinate' value from the last row (last dictionary) in the list.

    Args:
        data_list (list): A list of dictionaries containing property data.

    Returns:
        land_coordinate: The value of 'land_coordinate' from the last dictionary, or None if not present.
    """
    if data_list:
        # Access the last dictionary in the list using negative indexing
        last_row = data_list[-1]
        # Extract the 'land_coordinate' value, or return None if it doesn't exist
        return last_row.get('land_coordinate', None)
    return None  # Return None if the list is empty


def get_property_coord(pcoord):
    """
    Fetch property data for a specific postal code from Vancouver open data.

    Args:
        pcoord (str): The coordinate to search for.

    Returns:
        Coordinates: The geometry coordinates of the property.
    """
    base_url = 'https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/property-addresses/records'

    # Properly format the WHERE clause with LIKE
    params = {
        'where': f"pcoord='{pcoord}'",
        'limit': 100  # Optional: Limit the number of records returned
    }

    # Make the request
    response = requests.get(base_url, params=params)

    # Return the response object or handle errors as needed
    if response.status_code == 200:
        data = response.json()
        if 'results' in data and data['results']:
            return data['results'][0]['geom']['geometry']['coordinates']
        else:
            return None  # Handle case where no data is found
    else:
        return f"Error: {response.status_code}"


def get_property_street(civic_number):
    """
    Fetch unique street names for a specific civic number from Vancouver open data, grouped by street name.

    Args:
        civic_number (str or int): The civic number to search for.

    Returns:
        list: A sorted list of unique street names.
    """
    base_url = 'https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/property-tax-report/records'

    # Update the params to include group_by for street_name
    params = {
        'where': f"to_civic_number='{civic_number}'",  # Insert the civic number as a raw string
        'group_by': 'street_name',  # Group the results by street name
        'limit': 100  # Optional: Limit the number of records returned
    }

    # Make the request
    response = requests.get(base_url, params=params)

    # Check if the response is successful
    if response.status_code == 200:
        data = response.json()

        # Extract street names from the response
        if 'results' in data:
            street_name_set = {item['street_name'] for item in data['results']}
            return sorted(street_name_set)
        else:
            return []
    else:
        return f"Error: {response.status_code}"


def plot_property_from_dict_plotly(data_list):
    """
    Generate and display a stacked bar chart for property data from a list of dictionaries using Plotly,
    with total value as a data label above the bars and value change as a percentage.

    Args:
        data_list (list): A list of dictionaries containing property data with relevant fields.

    Returns:
        None: The function displays the Plotly plot.
    """
    # Extract data from the list of dictionaries
    years = [item['report_year'] for item in data_list]
    land_values = [item['current_land_value'] for item in data_list]
    improvement_values = [item['current_improvement_value'] for item in data_list]
    value_changes = [item['value_change'] for item in data_list]  # Assuming this is a percentage already

    # Calculate total value for each year
    total_values = [land + improvement for land, improvement in zip(land_values, improvement_values)]

    # Create the stacked bar chart
    fig = go.Figure()

    # Add bar for land value
    fig.add_trace(go.Bar(
        x=years,
        y=land_values,
        name='Land Value',
        text=[f'${val / 1e6:.2f}M' for val in land_values],  # Add labels inside the bars
        textposition='auto',
        marker_color='#129ad7',  # Color for land values
        textfont=dict(
            size=14,  # Text size for land value labels
            color='white',  # Text color for labels
        )
    ))

    # Add bar for improvement value (stacked on top of land value)
    fig.add_trace(go.Bar(
        x=years,
        y=improvement_values,
        name='Improvement Value',
        text=[f'${val / 1e6:.2f}M' for val in improvement_values],  # Add labels inside the bars
        textposition='auto',
        marker_color='#0abf8e',  # Color for improvement values
        textfont=dict(
            size=14,  # Text size for improvement value labels
            color='white',  # Text color for labels
        )
    ))

    # Add total value and percentage change labels
    for year, total_value, value_change in zip(years, total_values, value_changes):
        # Label the total value above the bars
        fig.add_trace(go.Scatter(
            x=[year],
            y=[total_value],
            text=[f'${total_value / 1e6:.2f}M'],  # Total value label
            mode='text',
            textposition='top center',
            textfont=dict(
                size=16,  # Increase size of total value labels
                color='black',  # Color for the total value label
            ),
            showlegend=False  # Hide the legend for these labels
        ))

        # Conditional color for value change (positive = green, negative = red)
        value_change_color = '#0abf8e' if value_change > 0 else '#f36870'

        # Add the percentage change label above the total value
        fig.add_trace(go.Scatter(
            x=[year],
            y=[total_value + 0.05 * total_value],  # Position the percentage change slightly higher
            text=[f'{value_change:.2f}%'],  # Already a percentage
            mode='text',
            textposition='top center',
            textfont=dict(
                size=14,  # Size for percentage labels
                color=value_change_color,  # Green if positive, red if negative
            ),
            showlegend=False  # Hide the legend for these labels
        ))

    # Update layout to create a stacked bar chart
    fig.update_layout(
        barmode='stack',  # Stack the bars
        plot_bgcolor='white',
        showlegend=True,
        margin=dict(t=20, b=40),
        legend=dict(
            orientation="h",  # Horizontal legend
            yanchor="bottom",
            y=1.1,  # Moves legend above the plot
            xanchor="center",
            x=0.5  # Centers the legend
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=years,
            tickfont=dict(size=18, color='#0e2f42')  # Set size of x-axis labels
        ),
        yaxis=dict(
            showticklabels=False,  # Hide y-axis labels
            title="Value in Millions",
        )
    )

    # Show the plot
    return fig


def plot_pct_change_plotly(data_dict, property_avg_change):
    """
    Generate and display a Plotly plot for the 'value_change' column from the given dictionary, grouped by 'report_year'.
    Add the average value for each year as a KDE curve, plot a single overall average point for the neighbourhood,
    and an additional point for the property average change.

    Args:
        data_dict (dict): A dictionary where each key is a year and the value is a list of records with 'value_change' and 'report_year'.
        property_avg_change (float): The average percentage change for the property to be plotted.

    Returns:
        Plotly Figure
    """
    # Create a figure
    fig = go.Figure()

    # Prepare lists to hold all the values for percentage change and report year
    all_pct_changes = []
    all_report_years = []

    # Iterate through the dictionary to gather pct_change and report_year data
    for year, records in data_dict.items():
        for record in records:
            if 'value_change' in record and record['value_change'] is not None:
                all_pct_changes.append(record['value_change'])
                all_report_years.append(record['report_year'])

    # Convert to NumPy arrays for easier processing
    all_pct_changes = np.array(all_pct_changes)
    all_report_years = np.array(all_report_years)

    # Ensure there are valid values for percentage changes
    if len(all_pct_changes) == 0:
        raise ValueError("No valid 'value_change' data found in the dictionary.")

    # Get unique years in sorted order
    unique_years = sorted(np.unique(all_report_years))

    # Define a color palette for the KDE plots
    colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A']

    # Track the maximum y-value from KDEs to dynamically adjust the y-axis
    max_y_value = 0

    # Prepare the x-values dynamically based on the KDE computation
    x_values = np.linspace(all_pct_changes.min() - 2, all_pct_changes.max() + 2, 1000)

    # Plot KDE curves for each year
    for i, year in enumerate(unique_years):
        # Filter data for the current year
        yearly_pct_changes = all_pct_changes[all_report_years == year]

        # Skip years that have less than 2 data points (insufficient data to plot a KDE)
        if len(yearly_pct_changes) < 2:
            continue

        # Compute the KDE manually
        kde = gaussian_kde(yearly_pct_changes)
        kde_values = kde(x_values)

        # Update max_y_value if this KDE has a higher peak
        max_y_value = max(max_y_value, kde_values.max())

        # Plot the KDE as a filled curve
        fig.add_trace(go.Scatter(
            x=x_values, y=kde_values,
            fill='tozeroy', mode='lines', name=f'{year}',
            line=dict(color=colors[i % len(colors)], width=2),
            hoverinfo='name+x+y'
        ))

    # Calculate the overall average percentage change across all years
    overall_avg = np.mean(all_pct_changes)

    # Set the y-axis maximum to slightly above the highest KDE curve
    y_max = max_y_value * 1.1  # Adjust the y-axis to be 10% higher than the highest peak

    # Plot the neighbourhood overall average point
    fig.add_trace(go.Scatter(
        x=[overall_avg],
        y=[0.6 * y_max],  # Set the point at 60% of the max y value
        mode='markers',
        name='Neighbourhood Average',
        marker=dict(color='#0abf8e', size=12, symbol='circle', line=dict(width=2, color='white')),
        hoverinfo='name+x'
    ))

    # Add a vertical dotted line from the X-axis to the neighbourhood average point
    fig.add_trace(go.Scatter(
        x=[overall_avg, overall_avg],
        y=[0, 0.6 * y_max],  # Set the y-range to align with the new point position
        mode='lines',
        line=dict(color='#0abf8e', width=2, dash='dot'),
        showlegend=False
    ))

    # Add a label for the neighbourhood overall average point showing the percentage
    fig.add_trace(go.Scatter(
        x=[overall_avg],
        y=[0.65 * y_max],  # Slightly above the point to place the label
        mode='text',
        text=[f'{overall_avg:.2f}% (Neighbourhood)'],
        textposition='top center',
        showlegend=False,
        textfont=dict(size=14, color='#0abf8e')
    ))

    # Plot the property average change point
    fig.add_trace(go.Scatter(
        x=[property_avg_change],
        y=[0.4 * y_max],  # Set the point at 40% of the max y value
        mode='markers',
        name='Property Average',
        marker=dict(color='#129ad7', size=12, symbol='diamond', line=dict(width=2, color='white')),
        hoverinfo='name+x'
    ))

    # Add a vertical dotted line from the X-axis to the property average point
    fig.add_trace(go.Scatter(
        x=[property_avg_change, property_avg_change],
        y=[0, 0.4 * y_max],  # Set the y-range to align with the property point
        mode='lines',
        line=dict(color='#129ad7', width=2, dash='dot'),
        showlegend=False
    ))

    # Add a label for the property average point showing the percentage
    fig.add_trace(go.Scatter(
        x=[property_avg_change],
        y=[0.45 * y_max],  # Slightly above the point to place the label
        mode='text',
        text=[f'{property_avg_change:.2f}% (Property)'],
        textposition='top center',
        showlegend=False,
        textfont=dict(size=14, color='#129ad7')
    ))

    # Customize the layout
    fig.update_layout(
        title='Percentage Change by Year, Neighbourhood, and Property Average',
        xaxis_title='Percentage Change (%)',
        yaxis_title=None,
        xaxis=dict(showgrid=False),  # Remove gridlines, let Plotly determine the x-axis range
        yaxis=dict(range=[0, y_max], showticklabels=False, zeroline=False, showgrid=False),  # Dynamically adjust y-axis
        legend_title='Report Year',
        hovermode='x',
        template='plotly_white'
    )

    return fig


def extract_last_neighbourhood_code(data_list):
    """
    Extract the 'neighbourhood_code' from the last row (last dictionary) in the list.

    Args:
        data_list (list): A list of dictionaries containing property data.

    Returns:
        str: The 'neighbourhood_code' from the last dictionary, or None if not present.
    """
    if data_list:
        # Access the last dictionary in the list using negative indexing
        last_row = data_list[-1]
        # Extract the 'neighbourhood_code' value, or return None if it doesn't exist
        return last_row.get('neighbourhood_code', None)
    return None  # Return None if the list is empty


def get_property_data_by_neighbourhood(property_postal_code, year):
    """
    Fetch property data for a specific postal code and year from Vancouver open data.

    Args:
        property_postal_code (str): The postal code to search for.
        year (int): The report year.

    Returns:
        list: A list of filtered property data for the given postal code and year.
    """
    base_url = 'https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/property-tax-report/records'

    # Format the WHERE clause with the specific postal code and year
    params = {
        'where': f"neighbourhood_code='{property_postal_code}' AND from_civic_number IS NULL AND report_year='{year}'",
        'limit': 100  # Optional: Limit the number of records returned
    }

    # Make the request
    response = requests.get(base_url, params=params)

    # If the response is successful
    if response.status_code == 200:
        data = response.json()

        # Check if 'results' exists in the response
        if 'results' in data:
            results = data['results']

            # Keys to keep
            keys_to_keep = ["pid", "legal_type", 'land_coordinate', "zoning_district", "from_civic_number",
                            "to_civic_number", "street_name",
                            'current_land_value', 'current_improvement_value', 'previous_land_value',
                            'previous_improvement_value',
                            'year_built', 'tax_levy', 'neighbourhood_code', 'report_year']

            # Extract specific columns (keys) from the JSON response
            filtered_data = [{key: item.get(key) for key in keys_to_keep} for item in results]

            for item in filtered_data:
                # Handle None values and set them to 0 if not present
                current_land_value = item.get('current_land_value') or 0
                current_improvement_value = item.get('current_improvement_value') or 0
                previous_land_value = item.get('previous_land_value') or 0
                previous_improvement_value = item.get('previous_improvement_value') or 0

                item['total_value'] = current_land_value + current_improvement_value
                item['previous_value'] = previous_land_value + previous_improvement_value

                # Calculate value_change in percentage and round to 2 decimal places
                if item['previous_value'] > 0:
                    item['value_change'] = round(((item['total_value'] / item['previous_value']) - 1) * 100, 2)
                else:
                    item['value_change'] = None  # Set to None if no previous value for comparison

            # Return the filtered list of dictionaries with calculations
            return filtered_data
        else:
            return []  # Return an empty list if no 'results'
    else:
        return []  # Return an empty list on failure


# Main function to gather data for multiple years and accumulate into one big dictionary
def gather_property_data_for_years(civic_number, std_street, years):
    """
    Gather property data for multiple years and accumulate it into one big dictionary.

    Args:
        civic_number (str or int): The civic number to search for.
        std_street (str): The standard street name to search for.
        years (list): A list of years to retrieve data for.

    Returns:
        dict: A dictionary containing data for all years.
    """
    # Step 1: Get property data using civic number and street
    property_data = get_property_data(civic_number, std_street)

    # Step 2: Extract 'neighbourhood_code' from the last row
    neighbourhood_code = extract_last_neighbourhood_code(property_data)

    # Initialize an empty dictionary to store the accumulated data
    all_data = {}

    if neighbourhood_code:
        # Step 3: Loop through each year and collect data
        for year in years:
            property_data_by_year = get_property_data_by_neighbourhood(neighbourhood_code, year)

            # Step 4: Append the results for the current year to the all_data dictionary
            all_data[year] = property_data_by_year
    else:
        print("No neighbourhood code found in the last row.")

    return all_data

def format_tax_levy(value):
    return f"${value:,.2f}" if value is not None else "N/A"


def extract_average_value_change(data_list):
    """
    Extract the 'value_change' from each dictionary in the list and return the average value.

    Args:
        data_list (list): A list of dictionaries containing property data.

    Returns:
        float: The average 'value_change' across all dictionaries, or None if no valid values are found.
    """
    value_changes = []

    # Iterate over each dictionary in the list
    for record in data_list:
        # Extract 'value_change' if present and not None
        value_change = record.get('value_change', None)
        if value_change is not None:
            value_changes.append(value_change)

    # If there are valid value_change entries, calculate and return the average
    if value_changes:
        return np.mean(value_changes)

    # Return None if no valid 'value_change' values were found
    return None


# Initialize the Dash app and set the title
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "🏡 AreaCheck - Explore Property Insights 🏙️"  # This will change the browser tab title to "AreaCheck"

# Create the layout for the app
app.layout = dbc.Container([  # Use dbc.Container for better spacing control

    # Navbar component with logo and blue text/nav items
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("GitHub", href="https://github.com/ronanmccormack-ca/AreaCheck", style={"color": "#129ad7", "font-size": "18px"})),
            dbc.NavItem(dbc.NavLink("LinkedIn", href="https://www.linkedin.com/in/ronan-mccormack/", style={"color": "#129ad7", "font-size": "18px"})),
            dbc.NavItem(dbc.NavLink("Contact Me", href="mailto:info@datahouse.ca", style={"color": "#129ad7", "font-size": "18px"})),
        ],
        brand=html.Div([
            html.Img(src="assets/logo.png", height="90px", style={"margin-right": "10px"}),
            html.Span("AreaCheck", style={"color": "#129ad7", "font-size": "24px", "font-weight": "bold"})
        ], style={"display": "flex", "align-items": "center"}),
        brand_href="#",
        color="white",
        dark=True,
    ),

    # Page Title with some margin and centered text
    html.H1(
        "Search City of Vancouver Property Data by Address",
        style={
            'marginTop': '20px',
            'marginBottom': '20px',
            'color': '#113146',
            'textAlign': 'center'  # Center the text
        }
    ),

    # Input for civic number, street dropdown, and unit number dropdown with blue border, titles, and margin
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Label("Street Number", style={'font-size': '16px', 'font-weight': 'bold', 'color': '#113146'}),
                dcc.Input(
                    id="civic-number-input",
                    type="number",
                    placeholder="Enter Street Number",
                    style={
                        'width': '100%',
                        'border-radius': '5px',
                        'padding': '10px'
                    }
                ),
                html.Label("Unit Number",
                           style={'font-size': '16px', 'font-weight': 'bold', 'color': '#113146',
                                  'margin-top': '10px'}),
                dcc.Input(
                    id="unit-number-input",
                    type="text",
                    placeholder="Enter Unit Number (optional)",
                    style={
                        'width': '100%',
                        'border-radius': '5px',
                        'padding': '10px',
                        'margin-top': '10px'
                    }
                )
            ], width=6),
            dbc.Col([
                html.Label("Street Name", style={'font-size': '16px', 'font-weight': 'bold', 'color': '#113146'}),
                dcc.Dropdown(
                    id='street-dropdown',
                    options=[],
                    placeholder="Select a street",
                    style={
                        'width': '100%',
                        'border-radius': '5px',
                        'padding': '10px'
                    }
                ),
                # Use dbc.Button for better button styling
                dbc.Button(
                    'Search',
                    id='search-button',
                    color="primary",  # Make the button blue
                    className="mt-4",  # Add some margin on top
                    style={'width': '100%', 'padding': '10px', 'border-radius': '5px'}  # Full width and better styling
                ),
                html.Div(id='property-warning', style={'margin-top': '10px'})  # Add warning div
            ], width=6),
        ], className="mb-4", style={
            'border': '2px solid #129ad7',
            'border-radius': '5px',
            'padding': '20px',
            'margin-bottom': '20px'
        })
    ], style={'padding': '40px'}),  # Add padding around the container

    # Section to display basic property information
    # Property Info Section
    dbc.Row([
        dbc.Col(
            html.Div(id='property-info'),
            width=6,  # Make the column narrower (half the width)
            className="mb-4",
            style={'textAlign': 'center'},  # Center the content inside the div
            # Offset by 3 columns to center it (as 6+3+3=12, making it centered)
            xs={"size": 10, "offset": 1},  # Adjust for extra-small devices
            sm={"size": 8, "offset": 2},  # Adjust for small devices
            md={"size": 6, "offset": 3},  # Adjust for medium and larger devices
        ),
    ]),

    # A container for both the map and the property graphs
    dbc.Row([

        # Div for the property graph
        dbc.Col(
            dcc.Graph(id='property-graph',style={'width': '100%'}),
            width=12, className="mb-4"
        ),
    ]),
    # A container for both the map and the property graphs
    dbc.Row([
        # Div for the neighbourhood graph
        dbc.Col(
            dcc.Graph(id='property-graph1',style={'width': '100%'}),
            width=12, className="mb-4"
        ),
    ]),

    # Div for the map graph
    dbc.Row([
        dbc.Col(
            dcc.Graph(id='map-graph',style={'width': '100%'}),
            width=12
        )
    ]),
], fluid=True)  # Make container fluid for better responsiveness


# Callback to update the dropdown when civic number changes
@app.callback(
    Output('street-dropdown', 'options'),
    [Input('civic-number-input', 'value')]
)
def update_dropdown(civic_number):
    if civic_number is not None:
        street_list = get_property_street(civic_number)
        return [{'label': street, 'value': street} for street in street_list]
    return []


@app.callback(
    [Output('property-info', 'children'),
     Output('property-graph', 'figure'),
     Output('property-graph1', 'figure'),
     Output('map-graph', 'figure'),
     Output('property-warning', 'children')],
    [Input('search-button', 'n_clicks')],  # Add button click as a trigger
    [State('civic-number-input', 'value'),  # Use State to keep inputs from being triggers
     State('unit-number-input', 'value'),
     State('street-dropdown', 'value')]
)
def display_property_data(n_clicks, civic_number, unit_number, std_street):
    # Ensure n_clicks is not None and is greater than 0
    if n_clicks and n_clicks > 0 and civic_number and std_street:
        # Check if 'from_civic_number' is needed based on unit number input
        from_civic_needed = has_from_civic_number(civic_number, std_street)

        # If from_civic_number is needed and unit_number is not provided, show a warning
        if from_civic_needed and not unit_number:
            warning_message = html.Div(
                "This address requires a unit number. Please enter a unit number.",
                style={'color': 'red', 'font-weight': 'bold'}
            )
            return html.Div(), go.Figure(), go.Figure(), go.Figure(), warning_message

        # Use the unit number (from_civic_number) if provided, otherwise use the street number logic
        if from_civic_needed and unit_number:
            property_data = get_property_data(civic_number, std_street, from_civic_number=unit_number)
        else:
            property_data = get_property_data(civic_number, std_street)

        # If no property data is found, return empty outputs
        if not property_data:
            return html.Div("No property data available."), go.Figure(), go.Figure(), go.Figure(), html.Div()

        # Extract the land coordinate and neighbourhood code from the last entry
        land_coordinate = extract_last_land_coordinate(property_data)
        neighbourhood_code = extract_last_neighbourhood_code(property_data)

        # Fetch neighbourhood data for 2020-2024
        neighbourhood_data = gather_property_data_for_years(civic_number, std_street, [2020, 2021, 2022, 2023, 2024, 2025])

        # Plot coordinates on the map if land_coordinate exists
        if land_coordinate:
            coordinates = get_property_coord(land_coordinate)
            if coordinates:
                # Swap them to [latitude, longitude]
                swapped_coords = [coordinates[1], coordinates[0]]
                coordinates = swapped_coords

                # Create the map with coordinates and improved title styling
                map_fig = go.Figure(go.Scattermapbox(
                    lat=[coordinates[0]],
                    lon=[coordinates[1]],
                    mode='markers',
                    marker=go.scattermapbox.Marker(
                        size=12,
                        color='#0abf8e'
                    ),
                    text=['Property Location']
                ))
                map_fig.update_layout(
                    title={
                        'text': "Property Location Map",  # Title text
                        'y': 0.95,  # Adjust the vertical position
                        'x': 0.5,  # Center the title horizontally
                        'xanchor': 'center',  # Make sure the title is centered
                        'yanchor': 'top',  # Anchor the title to the top
                    },
                    title_font={
                        'size': 24,  # Larger font size for the title
                        'color': '#113146',  # Use the same dark blue color for consistency
                        'family': 'Arial, sans-serif',  # Use the same font family for a professional look
                    },
                    margin={'t': 80},  # Add top margin to give space for the title
                    mapbox_style="open-street-map",
                    mapbox_center={"lat": coordinates[0], "lon": coordinates[1]},
                    mapbox_zoom=15,
                    height=600
                )
            else:
                map_fig = go.Figure()
        else:
            map_fig = go.Figure()

        # Create property info card
        property_info = dbc.Card(
            dbc.CardBody([
                html.H4("Property Information", className="card-title"),
                dbc.ListGroup([
                    dbc.ListGroupItem(f"Property ID: {property_data[-1]['pid']}"),
                    dbc.ListGroupItem(f"Zoning: {property_data[-1]['zoning_district']}"),
                    dbc.ListGroupItem(f"Year Built: {property_data[-1]['year_built']}"),
                    dbc.ListGroupItem(f"Latest Assessment: {property_data[-1]['report_year']}"),
                    dbc.ListGroupItem(f"Gross Taxes in {property_data[-1]['report_year']}: {format_tax_levy(property_data[-1]['tax_levy'])}")
                ])
            ]),
            color="#129ad7",
            inverse=True,
        )

        # Plot property data
        property_graph = plot_property_from_dict_plotly(property_data)
        property_graph.update_layout(
                title={
                    'text': "Property Value Overview",  # The text of the title
                    'y': 0.95,  # Adjust the title's vertical position, closer to the top (between 0 and 1)
                    'x': 0.5,  # Center the title horizontally
                    'xanchor': 'center',  # Ensures the title is centered
                    'yanchor': 'top',  # Ensures the title is at the top
                },
                title_font={
                    'size': 24,  # Larger font size for better readability
                    'color': '#113146',  # Title color
                    'family': 'Arial, sans-serif',  # Font family
                },
                margin={'t': 80},  # Top margin to give space for the title
                # Add any other layout settings if needed
            )

        # Calculate property average change
        property_avg_change = extract_average_value_change(property_data)

        # Plot neighbourhood data
        neighbourhood_graph = go.Figure()
        if neighbourhood_data:
            neighbourhood_graph = plot_pct_change_plotly(neighbourhood_data, property_avg_change)
            # Update layout for better title appearance
            neighbourhood_graph.update_layout(
                title={
                    'text': "Neighbourhood Value Change (%)",  # The text of the title
                    'y': 0.95,  # Adjust the title's vertical position, closer to the top (between 0 and 1)
                    'x': 0.5,  # Center the title horizontally
                    'xanchor': 'center',  # Ensures the title is centered
                    'yanchor': 'top',  # Ensures the title is at the top
                },
                title_font={
                    'size': 24,  # Larger font size for better readability
                    'color': '#113146',  # Title color
                    'family': 'Arial, sans-serif',  # Font family
                },
                margin={'t': 80},  # Top margin to give space for the title
                # Add any other layout settings if needed
            )

        return property_info, property_graph, neighbourhood_graph, map_fig, html.Div()

    # If no valid input or no data available
    return html.Div("No property data available."), go.Figure(), go.Figure(), go.Figure(), html.Div()


# Run the Dash app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))  # Default port 8050 if PORT is not set
    app.run_server(debug=False, host="0.0.0.0", port=port)