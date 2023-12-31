import streamlit as st
import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from PIL import Image
from openai import AzureOpenAI
from azure.search.documents.models import (
    VectorizedQuery,
)

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
    st.write("💬 Start a new Chat")
    if st.button('New Chat'):
        # Delete all the items in Session state
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

st.title("Chat with a Gordon Bot")
st.write("Idea here is you engage in a chat with :red[Gordon] about an email you need to send.  He will prompt you for information about your email.  When you are done chatting hit the :blue[Done Chatting] button and your email will be generated")

st.divider()

###     file operations

def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()
    
def chatbot(conversation):
        try:
            response = openai_client.chat.completions.create(
                        model=model, # model = "deployment_name".
                        messages=conversation
                    )
            text = response.choices[0].message.content
            
            return text, response.usage.total_tokens
        except Exception as oops:
            print(f'\n\nError communicating with OpenAI: "{oops}"')
            exit(5)


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

# use this for capturing an easy to read transcript of the chat conversation
all_messages = list()

if "messages_chatbot" not in st.session_state:
    st.session_state["messages_chatbot"] = [{"role": "assistant", "content": "Tell me what you want to say in your email?"}]

# display the flow of chat bubbles between user and assistant
for msg in st.session_state.messages_chatbot:
    #print(msg["content"])
    if msg["role"] == "user":
        st.chat_message(msg["role"], avatar=Image.open('../images/User.png')).write(msg["content"])
        all_messages.append('USER: %s' % msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message(msg["role"], avatar=Image.open('../images/Gordon.png')).write(msg["content"])
        all_messages.append('GORDON BOT: %s' % msg["content"])

if prompt := st.chat_input():
    # set the system message and user message into the session state
    st.session_state.messages_chatbot.append({"role": "system", "content": open_file('../system_01_intake.md')})
    st.session_state.messages_chatbot.append({"role": "user", "content": prompt})

    # now fill the user chat bubble and append to all_messages - this is used to make an easy to read conversation
    st.chat_message("user", avatar=Image.open('../images/User.png')).write(prompt)

    response = openai_client.chat.completions.create(
                        model=model, # model = "deployment_name".
                        messages=st.session_state.messages_chatbot
                    )
    msg = response.choices[0].message

    # add the response from the llm to the session state
    st.session_state.messages_chatbot.append({'role': 'assistant', 'content': msg.content})

    # now fill the assistant chat bubble and append to all_messages - this is used to make an easy to read conversation
    st.chat_message("assistant", avatar=Image.open('../images/Gordon.png')).write(msg.content)

st.divider()

with st.form("send_intake"):
        st.write("Click to start generating notes, suggestions and actions")
        submitted = st.form_submit_button("Done chatting ..... Write my email!")
        if submitted:
            conversation = list()
            conversation.append({'role': 'system', 'content': open_file('../system_02_prepare_notes.md')})
            text_block = '\n\n'.join(all_messages)
            chat_log = '<<BEGIN CHAT>>\n\n%s\n\n<<END CHAT>>' % text_block
            with st.expander("💬 Chat Log"):
                st.write(chat_log)
            conversation.append({'role': 'user', 'content': chat_log})
            with st.spinner('Creating notes...'):
                notes, tokens = chatbot(conversation)
            with st.expander("📖 Notes"):
                st.write(notes)

            #print('\n\nGenerating Hypothesis Report')
            conversation = list()
            conversation.append({'role': 'system', 'content': open_file('../system_03_email.md').replace('<<CONTEXT>>', search_api(notes))})
            conversation.append({'role': 'user', 'content': notes})
            with st.spinner('Creating email a la Gordon...'):
                email, tokens = chatbot(conversation)
            with st.expander("📩 Email"):
                st.write(email)