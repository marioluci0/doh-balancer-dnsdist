# Official python image
FROM python:3.14.2-bookworm

COPY main.py /
COPY requirements.txt /
COPY dns_responses.csv /

# Comands to run on the container
RUN pip install -r /requirements.txt