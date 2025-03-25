import yaml
from flask import (
    Flask,
    g,
    render_template,
    request,
    url_for,
    session,
    redirect,
    jsonify,
)
from dataregistry import DataRegistry
import pandas as pd
import numpy as np
import json
from datetime import datetime
import dataregistry

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session data


# Function to initialize DataRegistry only when needed
def get_data_registry():
    if "datareg" not in g:
        g.datareg = DataRegistry()
    return g.datareg


# Function to fetch and cache `columns_dict`
def get_columns_dict():
    if "columns_dict" not in g:
        datareg = get_data_registry()
        cols = datareg.Query.get_all_columns()
        tables = [x.split(".")[0] for x in cols]

        columns_dict = {}
        for t in np.unique(tables):
            columns_dict[t] = [c.split(".")[1] for c in cols if c.split(".")[0] == t]

        g.columns_dict = columns_dict  # Cache it in Flask's `g` object
    return g.columns_dict


# Function to load categories and queries from YAML
def load_categories_and_queries():
    """Load category and query configurations from a YAML file."""
    with open("./static/production_datasets.yaml", "r") as file:
        config = yaml.safe_load(file)

    # Process the query filters to create a human-readable representation
    categories = config.get("categories", [])
    for i, category in enumerate(categories):
        category["id"] = f"cat_{i}"
        for j, query_item in enumerate(category.get("queries", [])):
            # Add an ID for each query
            query_item["id"] = f"q_{j}"

            # Store original query details for execution
            query_item["original_query"] = query_item["query"].copy()

            # Create human-readable filters list
            query_item["filters"] = [
                f"{f[0]} {f[1]} {f[2]}" for f in query_item["query"]["filters"]
            ]

            # Store columns for display
            query_item["columns"] = query_item["query"]["columns"]

    return categories


@app.context_processor
def inject_now():
    return {"current_year": datetime.utcnow().year}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/query", methods=["GET", "POST"])
def query():
    if request.method == "POST":
        # Get form values
        tables = request.form.getlist("table[]")
        columns = request.form.getlist("column[]")
        operators = request.form.getlist("operator[]")
        values = request.form.getlist("value[]")
        return_columns = request.form.getlist("return_columns[]")
        schema = request.form.getlist("schema[]")

        # Store all query parameters in session
        session["query_tables"] = tables
        session["query_columns"] = columns
        session["query_operators"] = operators
        session["query_values"] = values
        session["return_columns"] = return_columns
        session["schema"] = schema

        # Generate filters
        filters = [
            get_data_registry().Query.gen_filter(f"{tab}.{col}", op, val)
            for tab, col, op, val in zip(tables, columns, operators, values)
            if tab and col and val
        ]  # Skip empty conditions

        session["filters"] = filters

        return redirect(url_for("results"))

    # Check if we're in a reset state
    is_reset = session.get("reset_state", False)

    # For GET requests, retrieve the previous query data from session if available
    # and if we're not in a reset state
    if not is_reset:
        previous_query = {
            "tables": session.get("query_tables", [])
            if isinstance(session.get("query_tables"), list)
            else [],
            "columns": session.get("query_columns", [])
            if isinstance(session.get("query_columns"), list)
            else [],
            "operators": session.get("query_operators", [])
            if isinstance(session.get("query_operators"), list)
            else [],
            "values": session.get("query_values", [])
            if isinstance(session.get("query_values"), list)
            else [],
            "return_columns": session.get("return_columns", [])
            if isinstance(session.get("return_columns"), list)
            else [],
            "schema": session.get("schema", ["lsst_desc_production"])
            if isinstance(session.get("schema"), list)
            else ["lsst_desc_production"],
        }
    else:
        # If in reset state, provide empty initial values
        previous_query = {
            "tables": [],
            "columns": [],
            "operators": [],
            "values": [],
            "return_columns": [],
            "schema": ["lsst_desc_production"],
        }

    # Make previous_query available to the template as JavaScript
    previous_query_json = json.dumps(previous_query)

    return render_template(
        "query.html",
        columns_dict=get_columns_dict(),
        previous_query=previous_query,
        previous_query_json=previous_query_json,
    )


@app.route("/run_prebuilt_query", methods=["POST"])
def run_prebuilt_query():
    """Run a prebuilt query selected from the production datasets page."""
    category_name = request.form.get("category_name")
    query_title = request.form.get("query_title")

    # Load categories and queries
    categories = load_categories_and_queries()

    try:
        # Find the category and query by name
        selected_category = None
        selected_query = None

        for category in categories:
            if category["name"] == category_name:
                selected_category = category
                for query in category["queries"]:
                    if query["title"] == query_title:
                        selected_query = query
                        break
                break

        if not selected_category or not selected_query:
            raise ValueError(
                f"Could not find query with title '{query_title}' in category '{category_name}'"
            )

        # Extract query details
        query_filters = selected_query["original_query"]["filters"]
        return_columns = selected_query["original_query"]["columns"]

        # Generate filter objects
        data_registry = get_data_registry()
        filters = [
            data_registry.Query.gen_filter(f[0], f[1], f[2]) for f in query_filters
        ]

        # Prepare query data for the results page
        session["query_title"] = selected_query["title"]
        session["query_description"] = selected_query["description"]
        session["filters"] = filters
        session["return_columns"] = return_columns
        session["schema"] = [
            "lsst_desc_production"
        ]  # Default schema for production datasets

        # Additionally store for the query builder if the user wants to modify
        query_tables = []
        query_columns = []
        query_operators = []
        query_values = []

        for f in query_filters:
            table_column = f[0].split(".")
            if len(table_column) == 2:
                query_tables.append(table_column[0])
                query_columns.append(table_column[1])
                query_operators.append(f[1])
                query_values.append(f[2])

        session["query_tables"] = query_tables
        session["query_columns"] = query_columns
        session["query_operators"] = query_operators
        session["query_values"] = query_values

        # Clear reset state if it exists
        if "reset_state" in session:
            session.pop("reset_state")

        return redirect(url_for("results"))
    except Exception as e:
        # Prepare error message
        error_message = f"Error loading the selected query: {str(e)}"

        # Store error in session to display on the results page
        session["query_error"] = error_message

        return redirect(url_for("production_datasets"))


@app.route("/reset_query")
def reset_query():
    """Clear all query-related data from the session and redirect to the query page."""
    # Remove all query-related keys from session
    session.pop("query_tables", None)
    session.pop("query_columns", None)
    session.pop("query_operators", None)
    session.pop("query_values", None)
    session.pop("return_columns", None)
    session.pop("filters", None)
    session.pop("query_title", None)
    session.pop("query_description", None)

    # Keep schema as default
    session["schema"] = ["lsst_desc_production"]

    # Set a flag to indicate we're coming from reset
    session["reset_state"] = True

    return redirect(url_for("query"))


@app.route("/clear_reset_state", methods=["POST"])
def clear_reset_state():
    """Clear the reset state flag from the session."""
    session.pop("reset_state", None)
    return jsonify({"status": "success"})


@app.route("/clear_query_session", methods=["POST"])
def clear_query_session():
    """Completely clear all query-related data from the session."""
    # Reset everything in session related to queries
    keys_to_clear = [
        "query_tables",
        "query_columns",
        "query_operators",
        "query_values",
        "return_columns",
        "filters",
        "reset_state",
        "query_title",
        "query_description",
    ]

    for key in keys_to_clear:
        session.pop(key, None)

    # Reset schema to default
    session["schema"] = ["lsst_desc_production"]

    return jsonify(
        {
            "status": "success",
            "message": "Query session completely cleared",
            "cleared_keys": keys_to_clear,
        }
    )


@app.route("/results")
def results():
    # Check for query error
    if "query_error" in session:
        error_message = session.pop("query_error")
        return render_template("results.html", error=error_message)

    filters = session.get("filters", [])
    return_columns = session.get("return_columns", [])
    schema = session.get("schema", [])[0] if session.get("schema") else ""
    query_title = session.get("query_title", "Query Results")
    query_description = session.get("query_description", "")

    try:
        tmp_datareg = get_data_registry()
        df = tmp_datareg.Query.find_datasets(
            return_columns, filters, return_format="dataframe"
        )

        # Generate HTML table
        table_html = (
            df.to_html(classes="table table-striped", index=False)
            if not df.empty
            else ""
        )

        # Get row count for display
        rows_count = len(df)

        return render_template(
            "results.html",
            table=table_html,
            schema=schema,
            return_columns=return_columns,
            filters=filters,
            rows_count=rows_count,
            query_title=query_title,
            query_description=query_description,
        )
    except Exception as e:
        error_message = f"Query execution failed: {str(e)}"
        return render_template(
            "results.html",
            error=error_message,
            schema=schema,
            return_columns=return_columns,
            filters=filters,
            query_title=query_title,
            query_description=query_description,
        )


@app.route("/production_datasets")
def production_datasets():
    """Render the production datasets page with prebuilt queries from the YAML config."""
    categories = load_categories_and_queries()

    # Check for error message in session
    error = None
    if "query_error" in session:
        error = session.pop("query_error")

    return render_template(
        "production_datasets.html", categories=categories, error=error
    )


@app.route("/registry_stats")
def registry_stats():
    """Generate and display basic statistics from the dataregistry."""
    datareg = get_data_registry()

    # Get dataregistry version and database schema version
    version_info = {
        "dataregistry_version": dataregistry.__version__,
        "db_schema_version": datareg.db_connection.metadata.get(
            "schema_version", "Unknown"
        )
        if hasattr(datareg, "db_connection")
        and hasattr(datareg.db_connection, "metadata")
        else "Unknown",
        "prod_schema_version": datareg.db_connection.metadata.get(
            "prod_schema_version", "Unknown"
        )
        if hasattr(datareg, "db_connection")
        and hasattr(datareg.db_connection, "metadata")
        else "Unknown",
    }

    # Create filters for production and working schemas
    production_filter = datareg.Query.gen_filter(
        "dataset.owner_type", "==", "production"
    )
    working_filter = datareg.Query.gen_filter("dataset.owner_type", "!=", "production")

    # Get dataset counts by schema
    total_production = datareg.Query.aggregate_datasets(
        "dataset_id", agg_func="count", filters=[production_filter]
    )
    total_working = datareg.Query.aggregate_datasets(
        "dataset_id", agg_func="count", filters=[working_filter]
    )

    # Calculate total disk space
    total_disk_production = datareg.Query.aggregate_datasets(
        "total_disk_space", agg_func="sum", filters=[production_filter]
    )
    total_disk_working = datareg.Query.aggregate_datasets(
        "total_disk_space", agg_func="sum", filters=[working_filter]
    )

    # Format disk space in human-readable format
    def format_bytes(bytes_value):
        if bytes_value is None:
            return "0 B"

        # Convert to float to handle potential scientific notation
        bytes_value = float(bytes_value)

        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = bytes_value
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    disk_space = {
        "production": format_bytes(total_disk_production),
        "working": format_bytes(total_disk_working),
        "total": format_bytes(
            total_disk_production + total_disk_working
            if total_disk_production is not None and total_disk_working is not None
            else None
        ),
    }

    # Calculate total number of files
    total_files_production = datareg.Query.aggregate_datasets(
        "nfiles", agg_func="sum", filters=[production_filter]
    )
    total_files_working = datareg.Query.aggregate_datasets(
        "nfiles", agg_func="sum", filters=[working_filter]
    )

    total_files = {
        "production": total_files_production
        if total_files_production is not None
        else 0,
        "working": total_files_working if total_files_working is not None else 0,
        "total": (total_files_production or 0) + (total_files_working or 0),
    }

    return render_template(
        "registry_stats.html",
        version_info=version_info,
        total_datasets={
            "production": total_production,
            "working": total_working,
            "total": total_production + total_working,
        },
        disk_space=disk_space,
        total_files=total_files,
    )
