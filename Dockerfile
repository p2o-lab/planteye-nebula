# set base image (host OS)
FROM python:3.8

# set the working directory in the container
WORKDIR /nebula

# update and install components
RUN apt-get update -y

# install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy files into the working directory
COPY src/ src/
COPY config.yaml .
COPY main.py .

# command to run on container start
CMD [ "python", "main.py" ]
