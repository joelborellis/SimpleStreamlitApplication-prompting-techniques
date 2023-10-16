# app/Dockerfile

FROM python:3.10-slim

EXPOSE 8501

WORKDIR /

COPY . .

RUN pip install -r requirements.txt

CMD streamlit run ./app/Welcome.py
