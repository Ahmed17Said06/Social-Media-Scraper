from pymongo import MongoClient

# Connect to the MongoDB instance
client = MongoClient('mongodb://localhost:27017')
db = client['scraped_data_db']  # database name

# List all collections in the database
collections = db.list_collection_names()

print("Collections in the database:")
for collection_name in collections:
    print(collection_name)
