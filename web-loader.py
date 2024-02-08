from bs4 import BeautifulSoup
from datetime import datetime
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
from pympler.asizeof import asizeof
import json

#url = "http://localhost:8181"
url = "https://python.langchain.com/docs/integrations/document_loaders/"

#load_dotenv()

# variables
#source_path = os.environ['DOCS_DIR']

#source_files = os.listdir(source_path)
chunk_size = 200
chunk_overlap = 25

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

conn = connections.connect(host="127.0.0.1", port=19530)

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="metadata_type", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)
]
schema = CollectionSchema(fields=fields, description="vectorized facts")
collection = Collection(name="facts", schema=schema)
index_params={
    "metric_type":"IP",
    "index_type":"IVF_FLAT",
    "params":{"nlist":128}
}
collection.create_index(field_name="vector", index_params=index_params)

# on a huge dataset grpc can error due to size limits, so we need to break it into batches
batched_entries = []
batched_entries.append([])
batch_index = 0
batch_size = 0
max_batch_size = 60000000 # 67108864 is the true value but we're leaving a safety margin


date_time = datetime.now()
str_date_time = date_time.isoformat()


def LoadWeb(url):
    loader = RecursiveUrlLoader(url, max_depth=100)
    pages = loader.load_and_split()
    return [{
        "metadata_type": "web",
        "metadata": json.dumps({'source': x.metadata['source'], \
                                'title':  x.metadata['title'], \
                                'language':  x.metadata['language'], \
                                'ingest_date': str_date_time}),
        "content": x.page_content
    } for x in pages]


def Vectorize(pages):
    global batch_index
    global batch_size
    PageProgress = tqdm(total=len(pages))
    for page in pages:
        PageProgress.update(1)
        chunks = splitter.split_text(page["content"])
        for chunk in chunks:
            vect = stransform.encode(chunk)
            entry = {
                "metadata_type":page["metadata_type"],
                "metadata":page["metadata"],
                "text":chunk,
                "vector":vect
            }
            entry_size = asizeof(entry)
            if (batch_size + entry_size > max_batch_size):
                batched_entries.append([])
                batch_index = batch_index + 1
                batch_size = 0
            batched_entries[batch_index].append(entry)
            batch_size = batch_size + entry_size
        #insert each page's vectors
        # collection.insert([
        #     [x["metadata"] for x in entries],
        #     [x["text"] for x in entries],
        #     [x["vector"] for x in entries],
        # ])


#for file in source_files:
#    print(file)
#    pages = None
#    if (file.endswith(".pdf")):
#        pages = LoadPDF(source_path, file)
#    if (pages):
#        Vectorize(pages)

print(url)
pages = LoadWeb(url)
if (pages):
    Vectorize(pages)


for batch in batched_entries:
    collection.insert([
        [x["metadata_type"] for x in batch],
        [x["metadata"] for x in batch],
        [x["text"] for x in batch],
        [x["vector"] for x in batch],
    ])
