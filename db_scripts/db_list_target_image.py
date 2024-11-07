from pymongo import MongoClient
from gridfs import GridFS

# Connect to the MongoDB instance
client = MongoClient('mongodb://localhost:27017')
db = client['scraped_data_db']  # database name

# Initialize GridFS
fs = GridFS(db)

target_name = "Elon Musk"  # target name

# Find all files for this target
files = fs.find({"target": target_name})

print(f"Files stored in GridFS for target '{target_name}':")
for file in files:
    print(f"Filename: {file.filename}, Upload Date: {file.upload_date}, File ID: {file._id}")
