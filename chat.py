import os
import openai
from time import time, sleep
from halo import Halo
import textwrap
from dotenv import load_dotenv
from azure.search.documents.models import Vector  
from langchain.embeddings import OpenAIEmbeddings
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

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

###     file operations

def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
        return infile.read()

###     API functions

def chatbot(conversation, engine=model, temperature=0, max_tokens=2000):
    max_retry = 7
    retry = 0    

    while True:
        try:
            spinner = Halo(text='Thinking...', spinner='dots')
            spinner.start()
            #print(model)
            
            response = openai.ChatCompletion.create(engine=engine, messages=conversation, temperature=temperature, max_tokens=max_tokens)
            text = response['choices'][0]['message']['content']

            spinner.stop()
            
            return text, response['usage']['total_tokens']
        except Exception as oops:
            print(f'\n\nError communicating with OpenAI: "{oops}"')
            exit(5)

# Function to generate embeddings for title and content fields, also used for query embeddings
def generate_embeddings(text):
    response = openai.Embedding.create(
        input=text, engine="text-embedding-ada-002")
    embeddings = response['data'][0]['embedding']
    return embeddings

def search_api(query: str) -> str:  
    search_client = SearchClient(vector_store_address, index_name, credential_search)  
    vector = Vector(value=generate_embeddings(query), k=3, fields="contentVector")  

    r = search_client.search(  
        search_text=query,  
        vectors=[vector],
        select=["content"],
        top=3
    )  
    results = [doc['content'] for doc in r]
    print("\n".join(results))
    return "\n".join(results)

def chat_print(text):
    formatted_lines = [textwrap.fill(line, width=120, initial_indent='    ', subsequent_indent='    ') for line in text.split('\n')]
    formatted_text = '\n'.join(formatted_lines)
    print('\n\n\nCHATBOT:\n\n%s' % formatted_text)

if __name__ == '__main__':

    conversation = list()
    conversation.append({'role': 'system', 'content': open_file('system_01_intake.md')})
    user_messages = list()
    all_messages = list()
    print('\n\nWelcome to Lightfoot')

    
    ## INTAKE PORTION
    
    while True:
        # get user input
        text = input('\n\nYOU: ').strip()
        if text == 'DONE':
            break
        user_messages.append(text)
        all_messages.append('USER: %s' % text)
        conversation.append({'role': 'user', 'content': text})
        response, tokens = chatbot(conversation)
        conversation.append({'role': 'assistant', 'content': response})
        all_messages.append('INTAKE: %s' % response)
        print('\n\nINTAKE: %s' % response)
    
    ## CHARTING NOTES
    
    print('\n\nGenerating Intake Notes')
    conversation = list()
    conversation.append({'role': 'system', 'content': open_file('system_02_prepare_notes.md')})
    text_block = '\n\n'.join(all_messages)
    chat_log = '<<BEGIN INTAKE CHAT>>\n\n%s\n\n<<END INTAKE CHAT>>' % text_block
    save_file('logs/log_%s_chat.txt' % time(), chat_log)
    conversation.append({'role': 'user', 'content': chat_log})
    notes, tokens = chatbot(conversation)
    print('\n\nNotes version of conversation:\n\n%s' % notes)
    save_file('logs/log_%s_notes.txt' % time(), notes)
    
    ## GENERATING EMAIL

    print('\n\nGenerating Email')
    conversation = list()
    conversation.append({'role': 'system', 'content': open_file('system_03_email.md').replace('<<CONTEXT>>', search_api(notes))})
    conversation.append({'role': 'user', 'content': notes})
    report, tokens = chatbot(conversation)
    save_file('logs/log_%s_email.txt' % time(), report)
    print('\n\nEmail suggestion:\n\n%s' % report)