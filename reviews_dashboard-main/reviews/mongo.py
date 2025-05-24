# reviews/mongo.py
from django.conf import settings
from pymongo import MongoClient

# settings.MONGO_HOST will default to "mongo" (the service name in docker-compose)
client     = MongoClient(settings.MONGO_HOST, settings.MONGO_PORT)
db         = client["amazon"]
collection = db["reviews"]
