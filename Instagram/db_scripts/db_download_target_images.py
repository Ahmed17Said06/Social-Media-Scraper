# download_images.py

import os
import hashlib
from pymongo import MongoClient
from gridfs import GridFS

# Function to sanitize and shorten file names
def sanitize_filename(original_name, target, folder="./downloaded_images"):
    # Hash the original name to create a unique identifier
    name_hash = hashlib.md5(original_name.encode()).hexdigest()
    # Use the target name and hash as the new file name
    file_name = f"{target}_{name_hash}.jpg"  # Assuming files are images with '.jpg' extension
    return os.path.join(folder, file_name)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['instagram_scraper']
fs = GridFS(db)

# Define the target name
target_name = "cristiano"
download_directory = "./downloaded_images"

# Create download directory if it doesn't exist
if not os.path.exists(download_directory):
    os.makedirs(download_directory)

# Find and download files
print(f"Downloading files for target '{target_name}'...")
files = fs.find({"target": target_name})
for file in files:
    original_filename = file.filename
    file_path = sanitize_filename(original_filename, target_name, download_directory)
    
    # Write the file to the download directory
    with open(file_path, "wb") as f:
        f.write(file.read())
    print(f"Downloaded: {file_path}")
