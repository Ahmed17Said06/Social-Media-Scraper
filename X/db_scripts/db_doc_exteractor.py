from pymongo import MongoClient

# Connect to the MongoDB instance
client = MongoClient('mongodb://localhost:27017')
db = client['scraped_data_db']  # database name
collection = db['Elon Musk']  # collection name

# Fetch all documents
documents = collection.find()

# Iterate through and print each document
for doc in documents:
    print(doc)
