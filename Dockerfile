# Base image: python:3.11-slim
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt requirements.txt

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the files to the working directory
COPY . .

# Expose the port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
