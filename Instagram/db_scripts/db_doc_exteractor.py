from pymongo import MongoClient

# Connect to the MongoDB instance
client = MongoClient('mongodb://localhost:27017')
db = client['instagram_scraper']  # database name
collection = db['leomessi']  # collection name

# Fetch all documents
documents = collection.find()

# Iterate through and print each document
for doc in documents:
    print(doc)
