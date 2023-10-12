import requests
from bs4 import BeautifulSoup
import re

page = 'https://www.lightfoot.ca/lyrics.htm'
base_url = 'https://www.lightfoot.ca/'
grab = requests.get(page)
soup = BeautifulSoup(grab.text.replace("file:///C:/TEMP/GLsite/", ""), 'html.parser')

# opening a file in write mode
f = open("test1.txt", "w")
# traverse paragraphs from soup
for link in soup.find_all("a"):
    urls = link.get('href')

    with open('txt/www.lightfoot.ca/'+ urls[:-4] + ".txt", "w+", encoding="UTF-8") as f:
        # Get the text from the URL using BeautifulSoup
        soup = BeautifulSoup(requests.get(base_url+urls).text, "html.parser")

        # Get the text but remove the tags
        text = soup.get_text()
        new_text = re.sub(r'\(.*?\)', '', text)
        f.write(new_text.replace('\n\n', ' ').replace('\n', ' '))   
f.close()