import json
import os
import requests
# line below commented; future feature.
# import antigravity
from pymilvus import connections, Collection
from sentence_transformers import SentenceTransformer
#import argparse
from configobj import ConfigObj
#from tqdm import tqdm
import streamlit as st


# TODO add collection as an option
# TODO make these be web inputs for streamlit
#parser = argparse.ArgumentParser()
#parser.add_argument("-t", "--task", required=True,
#                    help="Required: What you want Concierge to do.")
#parser.add_argument("-p", "--persona",
#                    help="What personality or tone you want as the response")
#parser.add_argument("-e", "--enhancers", nargs="*",
#                    help="Comments to be added after the main response")
#parser.add_argument("-f", "--file",
#                    help="file to be used in prompt to Concierge")
#args = parser.parse_args()
#
#task = ConfigObj(f"prompter_config/tasks/{args.task}.concierge", list_values=False)
#
#persona = None
#if args.persona:
#    persona = ConfigObj(f"prompter_config/personas/{args.persona}.concierge", list_values=False)
#
#enhancer = None
#if args.enhancers:
#    enhancer = [ConfigObj(f"prompter_config/enhancers/{enhancer}.concierge", list_values=False) for enhancer in args.enhancers]
#
#source_file = None
#if args.file:
#    if not os.path.exists(args.file):
#        parser.error("The file %s does not exist!" % args.file)
#    else:
#        source_file = open(args.file, 'r')

### TODO add the streamlit enabling bits.
### have a form that grabs the needed user inputs

# get info for dropdown boxes

#tasks = ["test","foo","bar"]

#tasks = [f for f in listdir("../prompter_config/tasks") if isfile(join("../prompter_config/tasks", f))]
path = "/home/douglas/concierge/prompter_config/"
tasks = os.listdir(path+"tasks")
task_names = [file.split('.')[0] for file in tasks]

personas = os.listdir(path+"personas")
persona_names = [file.split('.')[0] for file in personas]

enhancers = os.listdir(path+"enhancers")
enhancer_names = [file.split('.')[0] for file in enhancers]



st.set_page_config(page_title="Prompter", page_icon="📣" )

st.markdown("# Prompter")
st.sidebar.header("Prompter")

with st.form(key='concierge_config_form'):
    st.write("Concierge config")
    task = st.selectbox("Task: what do you want Concierge to do?", options=(task_names), key=1)
    persona = st.selectbox("Persona: what tone do you want Conierge to have?", options=(persona_names), key=2)
    enhancers = st.multiselect("Enhancer: what enhancers do you want Concierge to have?", options=(enhancer_names), key=3)
    submit_button = st.form_submit_button("Submit")


st.write(
    """
    Tips:
    Concierge needs your help to understand what you want.
    - Set the task (what you want Concierge to "do")
    - Choose the tone (what personality style)
    - Pick the enhancers (final thoughts based on your prompt)
    """
)



task = ConfigObj(f"prompter_config/tasks/{task}.concierge", list_values=False)

if persona:
    persona = ConfigObj(f"prompter_config/personas/{persona}.concierge", list_values=False)

if enhancers:
    enhancers = [ConfigObj(f"prompter_config/enhancers/{enhancers}.concierge", list_values=False) for enhancer in args.enhancers]
#
#source_file = None
#if args.file:
#    if not os.path.exists(args.file):
#        parser.error("The file %s does not exist!" % args.file)
#    else:
#        source_file = open(args.file, 'r')




#task = ConfigObj(f"path"+task, list_values=False)
#st.write(task['greeting'])
#st.stop()

### VARs ###
# TODO will want to make this a select later
references = 5

# TODO several revs in the future... allow users to pick model.
# very much low priority atm
models = requests.get("http://localhost:11434/api/tags")
model_list = json.loads(models.text)['models']
if not next(filter(lambda x: x['name'].split(':')[0] == 'mistral', model_list), None):
    print('mistral model not found. Please wait while it loads.')
    request = requests.post("http://localhost:11434/api/pull", data=json.dumps({"name": "mistral"}), stream=True)
    current = 0
    pbar = tqdm(
        unit="B",
        unit_scale=True,
        unit_divisor=1024
    )
    for item in request.iter_lines():
        if item:
            value = json.loads(item)
            # TODO: display statuses
            if 'total' in value:
                if 'completed' in value:
                    current = value['completed']
                    # slight hackiness to set the initial value if resuming a download or switching files
                    if pbar.initial == 0 or pbar.initial > current:
                        pbar.initial = current
                pbar.total = value['total']
                pbar.n = current
                pbar.refresh()
    pbar.close()

stransform = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# TODO make this into variable up top, or move to config file
# will need to support non-local host better for very large deployments
# DB connection info
conn = connections.connect(host="127.0.0.1", port=19530)
# TODO make this be a selectable attribute
collection = Collection("facts")
collection.load()

search_params = {
    "metric_type": "IP"
}

while submit_button:

    #st.write("Task is: " + task)
    #st.write("Persona is: " + persona)
    # need to loop over the enhancers
    #st.write("Enhancers is/are:" + enhancers)

    with st.form(key="final_prompt_form"):
        st.write(task['greeting'])
        user_input = st.text_area("Please enter your request here", key=11)
        prompt_button = st.form_submit_button("Submit") 

    #st.stop()

    if prompt_button:
        response = collection.search(
            data=[stransform.encode(user_input)],
            anns_field="vector",
            param=search_params,
            limit=references,
            output_fields=["metadata_type", "metadata", "text"],
            expr=None,
            consistency_level="Strong"
        )

        context = ""
        sources = []
        for resp in response:
            for hit in resp:
                context = context + hit.entity.get("text")
                sources.append({
                   "type": hit.entity.get("metadata_type"),
                   "metadata": hit.entity.get("metadata")
                })

        print('\nResponding based on the following sources:')
        for source in sources:
            metadata = json.loads(source["metadata"])
            if source["type"] == "pdf":
                print(f'   PDF File: page {metadata["page"]} of {metadata["filename"]} located at {metadata["path"]}')
            if source["type"] == "web":
                print(f'   Web page: {metadata["source"]} scraped {metadata[ingest_date]}')

        prompt = task['prompt']

        if persona:
            prompt = persona['prompt'] + "\n\n" + prompt

        if enhancer:
            for enhancement in enhancer:
                prompt = prompt + "\n\n" + enhancement['prompt']

        prompt = prompt + "\n\nContext: " + context + "\n\nUser input: " + user_input

        if source_file:
            file_contents = source_file.read()
            prompt = prompt + "\n\nSource file: " + file_contents

        data={
            "model":"mistral",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post('http://127.0.0.1:11434/api/generate', data=json.dumps(data))

        result = json.loads(response.text)['response']
        print("\n\n")
        print(result)
        print("\n\n")

        # Force streamlit to prompt user to submit again
        submit_button = False
        prompt_button = False
