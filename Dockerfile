# Use Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]