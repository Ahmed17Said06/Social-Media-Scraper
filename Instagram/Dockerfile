# Use a Python 3.10 base image
FROM python:3.10-slim

# Install system dependencies required by Playwright (and for headless Chromium)
RUN apt-get update && apt-get install -y \
    cron \
    wget \
    curl \
    libx11-dev \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm-dev \
    libasound2 \
    libatspi2.0-0 \
    libnss3 \
    libxtst6 \
    libxss1 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    ca-certificates \
    libappindicator3-1 \
    libnotify4 \
    libvulkan1 \
    fonts-liberation \
    libu2f-udev \
    && rm -rf /var/lib/apt/lists/*


# Set the working directory inside the container
WORKDIR /root

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and download browsers (Chromium in this case)
RUN pip install playwright && playwright install --with-deps

# Copy your scraper code into the container
COPY . .

# Copy the crontab file into the container
COPY crontab /etc/cron.d/mycron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/mycron

# Apply the cron job
RUN crontab /etc/cron.d/mycron


# Set the environment variables (optional)
ENV STORAGE_FILE="/root/instagram_session.json"

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Install cronjob and ensure cron is running in the foreground with tailing logs
CMD service cron start && tail -f /var/log/cron.log
