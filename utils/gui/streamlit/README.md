# Indaleko Streamlit GUI

This directory contains a Streamlit-based graphical user interface for Indaleko, providing visual access to your personal index data.

## Features

- **Dashboard:** Overview of your indexed data with visualizations
- **Search:** Natural language search with faceted filtering
- **Analytics:** Data visualizations and insights
- **Activity:** Timeline of user activities and context
- **Settings:** Database configuration and preferences

## Architecture

The GUI is built with a modular, component-based architecture:

- **Components**: UI elements organized by function (dashboard, search, etc.)
- **Services**: Business logic and data access layer
- **Mock Objects**: Test implementations for development and demo mode

### Component Structure

```
utils/gui/streamlit/
├── app.py                  # Main application entry point
├── components/             # UI components
│   ├── __init__.py         # Component exports
│   ├── activity.py         # Activity timeline component
│   ├── analytics.py        # Analytics and visualization component
│   ├── common.py           # Shared UI utilities
│   ├── connection.py       # Database connection component
│   ├── dashboard.py        # Dashboard overview component
│   ├── search.py           # Search interface component
│   ├── settings.py         # Settings and configuration component
│   └── sidebar.py          # Navigation sidebar component
├── mock_modules.py         # Mock implementations for development
├── run.py                  # CLI runner
├── run_gui.bat             # Windows launcher
├── run_gui.sh              # Linux/macOS launcher
└── services/               # Business logic and data access
    ├── __init__.py         # Service exports
    ├── config.py           # Configuration services
    ├── database.py         # Database interaction services
    └── query.py            # Query execution services
```

## Quick Start

### Windows

```
run_gui.bat
```

### Linux/macOS

```
./run_gui.sh
```

## Manual Startup

If you prefer to run the application manually:

1. Make sure the Indaleko Python environment is activated
2. Install required packages: `pip install streamlit plotly pydeck pillow`
3. Set the INDALEKO_ROOT environment variable to the root of the Indaleko project
4. Run: `streamlit run app.py`

## Usage Guide

### Dashboard

The dashboard provides an overview of your indexed data, including:
- Database statistics (collections, documents, indexes)
- Storage distribution by volume
- File type distribution
- Activity timeline
- Quick search functionality

### Search

The search page allows you to:
- Execute natural language queries against your index
- View and filter search results
- Explore query execution plans (using "Explain query")
- Debug query execution (using "Debug mode")
- Access advanced search options

### Analytics

The analytics page provides:
- Deeper insights into storage utilization
- Activity patterns over time
- Relationship visualization
- Customizable data views

### Activity

The activity page shows:
- Timeline of user activities
- Context information for activities
- Location data (when available)
- Detailed activity listings

### Settings

The settings page allows configuration of:
- Database connections
- Collection management
- Indexing preferences
- User interface settings

## Advanced Features

### Query Execution

The search functionality follows a robust execution flow:
1. First tries to use Indaleko's query tools for natural language understanding
2. Falls back to direct AQL queries if query tools are unavailable
3. Applies timeout limits with `max_runtime` parameter
4. Uses multiple fallback queries with increasing permissiveness
5. Shows both query plans and results when in "Explain" mode

### Demo Mode

The application supports a demo mode with mock data. This is automatically enabled when a real database connection is not available.

## Development

### Adding New Components

1. Create a new file in the `components/` directory
2. Implement a render function that follows the pattern:
   ```python
   def render_component_name():
       """
       Render the component with a description of what it does
       """
       # Component implementation
   ```
3. Add the component to `components/__init__.py`
4. Update `app.py` to use the new component

### Adding New Services

1. Create a new file in the `services/` directory
2. Implement service functions
3. Add the service functions to `services/__init__.py`

### Data Normalization

When displaying complex data:
- Use the `normalize_for_display()` function to prepare data for dataframes
- For query plans, use the dedicated `display_query_plan()` function
- Handle errors gracefully with try/except blocks and fallbacks

## Troubleshooting

### Common Issues

- **Database Connection Errors:** Check your ArangoDB configuration in the `config` directory
- **Missing Dependencies:** Run `pip install streamlit plotly pydeck pillow`
- **Path Issues:** Ensure INDALEKO_ROOT is set correctly
- **Display Errors:** Complex data structures may need normalization for display

### Debug Mode

Enable debug mode in the application to see detailed diagnostic information:
- Connection debug mode shows database connection details
- Search debug mode shows query execution details
- Both help diagnose issues with database access and query execution

## License

This component is part of Indaleko and is licensed under GNU AGPL v3.