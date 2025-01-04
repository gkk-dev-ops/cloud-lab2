# Dockerfile
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the application code
COPY app /app

# Install dependencies
RUN pip install fastapi uvicorn

# Expose the application port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
