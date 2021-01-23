# set base image (host OS)
FROM python:3.8

# set the working directory in the container
WORKDIR /nebula

# copy files into the working directory
COPY src/ src/
COPY requirements.txt .
COPY config.yaml .
COPY main.py .

# install dependencies
RUN pip install -r requirements.txt

# command to run on container start
CMD [ "python", "main.py" ]