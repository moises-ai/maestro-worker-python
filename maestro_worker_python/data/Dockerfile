FROM python:3.8
# You may have the model on your machine for testing using docker-compose
# Don't commit the model to the repo and download it from storage during CI
# A Github actions example is given later on the Deployment section
COPY ./models /worker/models
WORKDIR /worker
COPY ./requirements.txt /worker/requirements.txt
RUN pip3 install -r requirements.txt
COPY ./ /worker
ENTRYPOINT maestro-server --worker /worker/worker.py --base_path /worker-example --port 8000