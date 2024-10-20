# Use a lightweight base image with Python
FROM python:3.12-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    cron \
    wget \
    unzip \
    curl \
    git \
    gnupg \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /root

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy the crontab file into the container
COPY crontab /etc/cron.d/mycron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/mycron

# Apply the cron job
RUN crontab /etc/cron.d/mycron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Start the cron service and the application
CMD ["sh", "-c", "cron && Xvfb :99 -ac & tail -f /var/log/cron.log"]
