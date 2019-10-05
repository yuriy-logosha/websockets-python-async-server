FROM python:alpine3.7
COPY . /
WORKDIR /
RUN pip install -r imports.txt
EXPOSE 1300:1300
CMD python ./server.py