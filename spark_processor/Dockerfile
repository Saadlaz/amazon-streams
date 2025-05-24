# spark_processor/Dockerfile
FROM bitnami/spark:3.5.0

USER root
# Install pip and necessary Python libs
RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install numpy scipy pymongo nltk requests

# Copy your code & model into /app
COPY . /app
WORKDIR /app
