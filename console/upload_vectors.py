import feedparser
import os
import pinecone
import numpy as np
import openai
import requests
from bs4 import BeautifulSoup
from retrying import retry
from dotenv import load_dotenv

load_dotenv()


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000)
def create_embedding(article):
    # vectorize with OpenAI text-emebdding-ada-002
    embedding = openai.Embedding.create(input=article, model="text-embedding-ada-002")
    print(embedding)
    return embedding["data"][0]["embedding"]


# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# get the Pinecone API key and environment
pinecone_api = os.getenv("PINECONE_API_KEY")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT")

pinecone.init(api_key=pinecone_api, environment=pinecone_env)

if "blog-index" not in pinecone.list_indexes():
    print("Index does not exist. Creating...")
    pinecone.create_index("blog-index", 1536)
else:
    print("Index already exists. Deleting...")
    pinecone.delete_index("blog-index")
    print("Creating new index...")
    pinecone.create_index("blog-index", 1536)

# set index; must exist
index = pinecone.Index("blog-index")

# URL of the RSS feed to parse
url = "https://blog.baeke.info/feed/"

# Parse the RSS feed with feedparser
feed = feedparser.parse(url)

# get number of entries in feed
entries = len(feed.entries)
print("Number of entries: ", entries)

post_texts = []
pinecone_vectors = []
for i, entry in enumerate(feed.entries[:50]):
    # report progress
    print("Create embedding for entry ", i, " of ", entries)

    r = requests.get(entry.link)
    soup = BeautifulSoup(r.text, "html.parser")
    article = soup.find("div", {"class": "entry-content"}).text

    # create embedding
    vector = create_embedding(article)

    # append tuple to pinecone_vectors list
    pinecone_vectors.append((str(i), vector, {"url": entry.link}))

# all vectors can be upserted to pinecode in one go
upsert_response = index.upsert(vectors=pinecone_vectors)

print("Vector upload complete.")
