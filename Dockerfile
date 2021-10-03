# Reference: https://docs.aws.amazon.com/lambda/latest/dg/python-image.html#python-image-base

# Get AWS lambda Docker image
FROM public.ecr.aws/lambda/python:3.9

# Copy script and dependencies
COPY main.py .
COPY requirements.txt .
RUN  pip install -r requirements.txt --target .

# Install chromedriver and headless chromium
RUN yum install -y unzip && \
    curl -SL https://chromedriver.storage.googleapis.com/2.43/chromedriver_linux64.zip > /tmp/chromedriver.zip && \
    curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-55/stable-headless-chromium-amazonlinux-2017-03.zip > /tmp/headless-chromium.zip && \
    unzip /tmp/chromedriver.zip -d /opt/ && \
    unzip /tmp/headless-chromium.zip -d /opt/

# Install chrome
RUN yum install -y https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm

# Set environment variables
ENV email some_email@example.com
ENV password some_random_password

# Run Python script from handler function
CMD [ "main.lambda_handler" ]
