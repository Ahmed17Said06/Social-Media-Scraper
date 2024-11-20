# download_images.py

import os
from pymongo import MongoClient
from gridfs import GridFS

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['scraped_data_db']
fs = GridFS(db)

# Define the target name
target_name = "kylian mbappe"
download_directory = "./downloaded_images"

# Create download directory if it doesn't exist
if not os.path.exists(download_directory):
    os.makedirs(download_directory)

# Find and download files
print(f"Downloading files for target '{target_name}'...")
files = fs.find({"target": target_name})
for file in files:
    filename = file.filename
    file_path = os.path.join(download_directory, filename)
    
    # Write the file to the download directory
    with open(file_path, "wb") as f:
        f.write(file.read())
    print(f"Downloaded: {file_path}")
