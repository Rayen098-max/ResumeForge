FROM python:3.11-slim

# Install LibreOffice and standard fonts for document rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-dejavu \
    fonts-liberation \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure outputs directory exists
RUN mkdir -p outputs

# Expose port (Render/Railway use dynamic port, but we map to 5000 inside)
EXPOSE 5000

# Set production env flag
ENV FLASK_ENV=production

# Start application via gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]
