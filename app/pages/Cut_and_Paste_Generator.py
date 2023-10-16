import streamlit as st
import os
import openai
from langchain.llms import OpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import Vector
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

openai.api_type = os.environ.get("AZURE_OPENAI_TYPE")
openai.api_base = os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
openai.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
model: str = os.environ.get("AZURE_OPENAI_MODEL_NAME")

vector_store_address: str = os.environ.get("AZURE_SEARCH_SERVICE_ENDPOINT")
vector_store_key: str = os.environ.get("AZURE_SEARCH_ADMIN_KEY")
model_embed: str = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
index_name: str = "lightfoot-vector-index"
credential_search = AzureKeyCredential(vector_store_key)

search_client = SearchClient(
        endpoint=vector_store_address,
        index_name=index_name,
        credential=credential_search,
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
        st.rerun()

st.title("Cut and Paste (or write) an Email")
st.write("Idea here is to take an email you might have already created and paste it in to be converted to a :red['Gordon Lightfoot'] email.  Or you can write an email in the text area.")

st.divider()

###     file operations

def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()

# Function to generate embeddings for title and content fields, also used for query embeddings
def generate_embeddings(text):
    response = openai.Embedding.create(
        input=text, engine="text-embedding-ada-002")
    embeddings = response['data'][0]['embedding']
    return embeddings

def search_api(query: str) -> str:  
    results = []
    search_client = SearchClient(vector_store_address, index_name, credential_search)  
    vector = Vector(value=generate_embeddings(query), k=5, fields="contentVector")  

    r = search_client.search(  
        search_text=query,  
        vectors=[vector],
        select=["content", "title"],
        top=5
    )  

    for doc in r:
        results.append(f"[CITATIONS:  {doc['title']}]" + "\n" + (doc['content']))
    #print("\n".join(results))
    return ("\n".join(results))

def chatbot(conversation):
 
    while True:
        try:
            response = openai.ChatCompletion.create(engine=model, temperature=0.0, max_tokens=2000, messages=conversation)
            text = response['choices'][0]['message']['content']
            
            return text, response['usage']['total_tokens']
        except Exception as oops:
            print(f'\n\nError communicating with OpenAI: "{oops}"')
            exit(5)

with st.form("mail_form"):
    email_to = st.text_input("To: <email address>", key="email_to")
    email_from = st.text_input("From: <your name>", key="email_from")
    email_text = st.text_area("Cut and Paste (or write) your email here:", "", key="email_text")
    submitted = st.form_submit_button("Make my email!")
    
    if submitted:
        conversation = list()
        conversation.append({'role': 'system', 'content': open_file('../system_01_prepare_notes_copy_paste.md')})
        #text_block = '\n\n'.join(all_messages)
        #chat_log = '<<BEGIN SELLER INTAKE CHAT>>\n\n%s\n\n<<END SELLER INTAKE CHAT>>' % text_block
        #with st.expander("💬 Chat Log"):
        #    st.write(chat_log)
        #save_file('logs/log_%s_chat.txt' % time(), chat_log)
        conversation.append({'role': 'user', 'content': f"[TO:  {email_to}]" + f"[FROM:  {email_from}]" + email_text})
        with st.spinner('Creating notes...'):
            notes, tokens = chatbot(conversation)
        with st.expander("📖 Notes"):
            st.write(notes)

        #print('\n\nGenerating Hypothesis Report')
        conversation = list()
        conversation.append({'role': 'system', 'content': open_file('../system_02_email_copy_paste.md').replace('<<CONTEXT>>', search_api(notes))})
        conversation.append({'role': 'user', 'content': notes})
        with st.spinner('Creating email a la Gordon...'):
            email, tokens = chatbot(conversation)
        with st.expander("📩 Email"):
            st.write(email)