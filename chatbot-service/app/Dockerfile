# Use an official Python runtime as a base image
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Install the required Python libraries (Flask and OpenAI client)
RUN pip install --no-cache-dir flask openai

# Copy the application code into the container
COPY app.py /app/

# Expose port 80 (the Flask app listens on 80)
EXPOSE 80

# Start the Flask server when the container launches
CMD ["python", "app.py"]
