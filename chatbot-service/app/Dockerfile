# Use an official Python runtime as a base image
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not use a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --without dev --no-interaction --no-ansi

# Copy the application code into the container
COPY app.py ./

# Expose port 8080 (the Flask app listens on 8080)
EXPOSE 8080

# Start the Flask server when the container launches
CMD ["python", "app.py"]
