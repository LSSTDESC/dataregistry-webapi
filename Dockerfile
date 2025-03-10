# This Dockerfile installs the webapi flask app requirements then runs the
# flask app webserver

# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Location of the datareg config (this will be mounted in)
ENV DATAREG_CONFIG=/app/datareg_config_files/datareg_config

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000
ENV FLASK_DEBUG=1

# Expose the port Flask runs on
EXPOSE 5000

# Command to run the application in development mode
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]
