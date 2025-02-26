# Use official Python image
FROM python:3.12

# Set the working directory
WORKDIR /app

# Install system dependencies for MySQL client
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Ensure gunicorn is installed
RUN pip install gunicorn

# Expose port and start the Django server
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "mwami.wsgi:application"]