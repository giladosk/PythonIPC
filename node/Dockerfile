FROM python:3

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "-u", "./inter_process_node.py" ]
