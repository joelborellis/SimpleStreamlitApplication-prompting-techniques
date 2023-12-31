import streamlit as st
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from azure.search.documents.models import (
    VectorizedQuery,
)
from dotenv import load_dotenv

load_dotenv()

# Search stuff
vector_store_address: str = os.environ.get("AZURE_SEARCH_SERVICE_ENDPOINT")
vector_store_key: str = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
index_name: str = os.environ.get("AZURE_SEARCH_INDEX_NAME")
credential_search = AzureKeyCredential(vector_store_key)

search_client = SearchClient(
        endpoint=vector_store_address,
        index_name=index_name,
        credential=credential_search,
    )

# OpenAI Stuff
model: str = os.environ.get("AZURE_OPENAI_MODEL_NAME")
model_embed: str = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")

openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version="2023-12-01-preview",
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
)


with st.sidebar:
    #st.button("New Chat", type="primary")
    st.write("📩 Start a new Email")
    if st.button('New Email'):
        # Delete all the items in Session state
        for key in st.session_state.keys():
            del st.session_state[key]
        st.session_state["email_text"] = ""
        st.session_state["email_to"] = ""
        st.session_state["email_from"] = ""
        st.rerun()

st.title("Cut and Paste (or write) an Email")
st.write("Idea here is to take an email you might have already created and paste it in to be converted to a :red[Gordon Lightfoot] email.  Or you can write an email in the text area.")

st.divider()

###     file operations

def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()

# Function to generate embeddings for title and content fields, also used for query embeddings
def generate_embeddings(text, model="text-embedding-ada-002"):
   text = text.replace("\n", " ")
   return openai_client.embeddings.create(input = [text], model=model).data[0].embedding

def search_api(query: str) -> str:  
    results = []
    vector_query = VectorizedQuery(vector=generate_embeddings(query), k_nearest_neighbors=5, fields="contentVector")
  
    r = search_client.search(  
        search_text=None,  
        vector_queries= [vector_query],
        select=["title", "sourcefile", "category", "content"],
    ) 

    for doc in r:
        results.append(f"[CITATIONS:  {doc['title']}]" + "\n" + (doc['content']))
    #print("\n".join(results))
    return ("\n".join(results))

def chatbot(conversation):
        try:
            #response = openai.ChatCompletion.create(engine=model, temperature=0.0, max_tokens=2000, messages=conversation)
            #text = response['choices'][0]['message']['content']

            response = openai_client.chat.completions.create(
                        model=model, # model = "deployment_name".
                        messages=conversation
                    )
            text = response.choices[0].message.content
            
            return text, response.usage.total_tokens
        except Exception as oops:
            print(f'\n\nError communicating with OpenAI: "{oops}"')
            exit(5)

with st.form("mail_form"):
    email_to = st.text_input("Recipient: <email address>", key="email_to")
    email_text = st.text_area("Cut and Paste (or write) your email here:", "", key="email_text")
    submitted = st.form_submit_button("Make my email!")
    
    if submitted:
        conversation = list()
        conversation.append({'role': 'system', 'content': open_file('../system_01_prepare_notes_copy_paste.md')})
        conversation.append({'role': 'user', 'content': f"[RECIPIENT:  {email_to}]" + " " + email_text})
        with st.spinner('Creating notes...'):
            notes, tokens = chatbot(conversation)
            #print(tokens)
        with st.expander("📖 Notes"):
            st.write(notes)

        conversation = list()
        conversation.append({'role': 'system', 'content': open_file('../system_02_email_copy_paste.md').replace('<<CONTEXT>>', search_api(notes))})
        conversation.append({'role': 'user', 'content': notes})
        with st.spinner('Creating email a la Gordon...'):
            email, tokens = chatbot(conversation)
        with st.expander("📩 Email"):
            st.write(email)