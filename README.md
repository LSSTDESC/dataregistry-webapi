# LSST DESC Data Registry Web Interface

A web interface for the LSST DESC Data Registry, providing an easy way to query and explore the datasets in the registry. This application is built with Flask and runs in Docker containers for easy deployment and development.

## Overview

This application provides:

- A web-based query builder for searching the data registry
- Pre-built queries for common data exploration tasks
- Results display with support for large datasets

## Architecture

The application consists of two main components:

1. **Web Server**: A Flask application that serves the web interface and handles queries
2. **Database**: A PostgreSQL database (the `dataregistry`)

## Getting Started

### Setup and Installation

1. Clone this repository:
   ```bash
   git clone git@github.com:LSSTDESC/dataregistry-webapi.git
   cd dataregistry-webapi
   ```

2. Start the Docker containers:
   ```bash
   docker-compose up -d
   ```

   This will:
   - Build the Flask application container
   - Start the PostgreSQL database container
   - Configure networking between the containers
   - Make the web application available on http://localhost:5000

3. To stop the containers:
   ```bash
   docker-compose down
   ```

### Development Mode

The application is configured to run in development mode by default, which includes:

- Live reloading of code changes
- Detailed error messages
- Flask debugging enabled

## Usage

Once the application is running, navigate to `http://localhost:5000` in your web browser.

### Building Custom Queries

1. Navigate to the Query Builder page
2. Select tables and columns to query
3. Add filters by specifying conditions
4. Select columns to display in results
5. Submit the query to see results

### Using Pre-built Queries

1. Navigate to the Production Datasets page
2. Browse the categories of available queries
3. Select a query to run
4. View the results and optionally modify the query

## Configuration

### Data Registry Configuration

For now the `dataregistry` config file is baked into the `Dockerfile`. You will have to alter this for your needs.

### Production Datasets

Pre-built queries are defined in the `static/production_datasets.yaml` file. Each query includes:

- A title and description
- The tables and columns to query
- The filters to apply
- The columns to display in results

## Dependencies

- Flask: Web framework
- lsstdesc-dataregistry: Python library for interacting with the LSST DESC Data Registry

## Troubleshooting

### Database Connection Issues

If the web application cannot connect to the database:

1. Check that both containers are running:
   ```bash
   docker-compose ps
   ```

2. Check the database logs:
   ```bash
   docker-compose logs database
   ```

3. Verify the database is healthy:
   ```bash
   docker-compose exec database pg_isready -U postgres
   ```
