# 🏡 AreaCheck - Explore Property Insights 🏙️

AreaCheck is a Dash-based web application that allows users to explore property data in the City of Vancouver. It provides detailed information about properties, neighborhood value changes, and property location maps using open data.

## 🌍 Live Application

The app is live and accessible at the following link:  
[https://areacheck.onrender.com](https://areacheck.onrender.com)

## 🚀 Features
- Search for properties by street number, street name, and unit number.
- View detailed property information, including zoning, year built, and tax levy.
- Visualize property value changes over the years with interactive graphs.
- Display neighborhood value change statistics and comparisons.
- Map property locations using geographical coordinates.

## 🌐 Data Source: City of Vancouver Open Data Portal

This app leverages the City of Vancouver's Open Data API to fetch and visualize property-related data. Specifically, the app interacts with datasets available through the [City of Vancouver Open Data Portal](https://opendata.vancouver.ca/explore/?disjunctive.features&disjunctive.theme&disjunctive.keyword&disjunctive.data-owner&disjunctive.data-team&sort=modified), making use of the property tax report and property address datasets.

### 🔗 API Endpoints Used
The app makes use of the following API endpoints from the City of Vancouver's Open Data Portal:

1. **Property Tax Report API**: This endpoint provides detailed information on properties in Vancouver, including data like civic numbers, street names, zoning districts, current and previous land values, and yearly tax levies. The app fetches and processes this data to display property details and generate visualizations based on the input provided by users.

2. **Property Address API**: This endpoint allows the app to fetch coordinates and geographical data for properties in Vancouver. It is used to retrieve the geographic coordinates needed to visualize the property location on a map.

### 🏘️ How the Data is Used

- The app allows users to input a street number and street name to search for property data.
- The app processes the API responses and calculates total property value, year-over-year value changes, and other relevant details.
- A neighborhood comparison is provided by fetching additional data based on the neighborhood code from the API and calculating average property value changes for a selected period (e.g., 2020–2024).
- The property’s geographical location is plotted on a map using the coordinates obtained from the API.

### 📄 API Documentation
For more detailed information on the datasets used and how the data is structured, you can visit the [City of Vancouver Open Data Portal](https://opendata.vancouver.ca/explore/?disjunctive.features&disjunctive.theme&disjunctive.keyword&disjunctive.data-owner&disjunctive.data-team&sort=modified).

## 🐍 Python Libraries Used

This app utilizes several key Python libraries for its functionality. Below is a list of the primary libraries used:

- **Dash**: A web application framework for building analytical web apps, used to create the interactive user interface.
- **Plotly**: A graphing library that enables the creation of interactive charts and plots, which are embedded into the app to visualize property data.
- **Pandas**: A powerful data analysis and manipulation library used to process the property data fetched from the API.
- **NumPy**: A library for numerical computations, which helps with data manipulation and mathematical operations.
- **Requests**: A simple HTTP library for making API requests to the City of Vancouver Open Data Portal.
- **Dash Bootstrap Components**: Used for styling the app’s layout with Bootstrap components to make it more responsive and visually appealing.
- **Scipy**: Specifically, the `gaussian_kde` function from the SciPy library is used to generate smooth curves for data visualization.

## 📄 License

This project is licensed under the MIT License. You are free to use, modify, and distribute this software as long as you include proper attribution. For more information, refer to the `LICENSE` file included in this repository.

## 📬 Contact Information

For any inquiries, questions, or feedback, please reach out to:

**DataHouse**  
Email: [info@datahouse.ca](mailto:info@datahouse.ca)

