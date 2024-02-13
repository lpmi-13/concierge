from dotenv import load_dotenv
from loaders.pdf import LoadPDF
from loader_functions import Insert, InitCollection
import os
import logging


### script init elements ###
logging.basicConfig(filename = './logs/concierge.log',
                    filemode = 'a', format = '%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()


### hard coded vars ###
collection_name = "facts"


### config loaded variables ###
if (os.path.isfile('./.env')) and (os.path.exists(os.environ['DOCS_DIR'])):
    source_path = os.environ['DOCS_DIR']
else:
    logging.critical("document directory not set, or path does not exist or is not readable.")
    exit()


### main code ###
source_files = os.listdir(source_path)
collection = InitCollection(collection_name)

for file in source_files:
    print(file)
    pages = None
    if (file.endswith(".pdf")):
        pages = LoadPDF(source_path, file)
    if (pages):
        Insert(pages, collection)
