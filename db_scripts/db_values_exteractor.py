from pymongo import MongoClient

# Connect to the MongoDB instance
client = MongoClient('mongodb://localhost:27017')
db = client['scraped_data_db']  # database name
collection = db['Elon Musk']  # collection name

# Fetch all documents
documents = collection.find()

# Specify the key you're interested in
key_to_list = "timestamp"  # the key you want to list

# Iterate through each document and print the value of the specified key
for doc in documents:
    if key_to_list in doc:
        print(doc[key_to_list])
    else:
        print(f"{key_to_list} not found in document with _id: {doc['_id']}")
