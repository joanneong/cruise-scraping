# cruise-scraping

Some simple web scraping to keep an eye on cruise prices.

## Table of contents
1. [How to use locally](#how-to-use-locally)
2. [How to use with AWS Lambda function](#how-to-use-with-aws-lambda-function)
3. [Caveats](#caveats)
4. [AWS lambda with Docker](#aws-lambda-with-docker)
5. [Troubleshooting with Docker](#troubleshooting-with-docker)

## How to use locally

1. Download this repository locally.
2. Install [Python 3](https://www.python.org/downloads/).
3. Go into the project base directory.
4. Create a virtual environment:
    ```
    python3 -m venv env
    ```
5. Activate the virtual environment:
    ```
    source env/bin/activate
    ```
6. Install project dependencies:
    ```
    pip install -r requirements.txt
    ```
7. Install a [driver for a browser](https://selenium-python.readthedocs.io/installation.html#drivers) on your computer (used by Selenium). Move the driver to the base project directory.
8. Run the Python script locally in the virtual environment:
    ```
    python main.py --email <email> --password <password> --delay <delay>
    ```
9. When done, deactivate the virtual environment:
    ```
    deactivate
    ```

## How to use with AWS Lambda function

Context: We want to have **something** to run the Python script daily even if our computers are not turned on. One way to do so is to use [AWS lambda functions](https://aws.amazon.com/lambda/).

To deploy the code to AWS, we have to:

1. Create an AWS account
2. Create an AWS lambda function
3. [Deploy the code as a .zip file archive](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html). In this example the file to be uploaded is `deployment-package.zip`.
    ```
    cd env/lib/python3.8/site-packages
    zip -r ../../../../aws-deployment/deployment-package.zip .

    cd ../../../..
    zip -g aws-deployment/deployment-package.zip main.py
    ```
4. Edit the Runtime settings > handlers section of the AWS lambda function to `main.lambda_handler` so that AWS lambda knows which Python function to call
5. [Add a time-based trigger for the function](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents.html)
6. Download [chromedriver 2.43](https://chromedriver.storage.googleapis.com/index.html?path=2.43/) and download severless-chrome, then package them into a single zip file.
    ```
    cd aws-deployment

    curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-55/stable-headless-chromium-amazonlinux-2017-03.zip > headless-chromium.zip

    unzip headless-chromium.zip

    rm headless-chromium.zip

    zip -r chromedriver.zip chromedriver headless-chromium
    ```
7. [Add the chromedriver and headless chromium as a layer to the AWS lambda function](https://dev.to/awscommunity-asean/creating-an-api-that-runs-selenium-via-aws-lambda-3ck3). 
8. Add the email and password variables as environment variables for the AWS lambda function.
9. Test the function.
10. See an error message:
    ```
    {
      "errorMessage": "Message: Service /opt/chromedriver unexpectedly exited. Status code was: 127\n",
      "errorType": "WebDriverException"
      ...
    }
    ```
LOL this doesn't seem to work, no idea why :(

For simplicity, the files needed for AWS deployment are saved in `/aws-deployment`.

## Caveats

1. chromedriver, Chrome and Chromium versions
    Different chromedriver versions support [different versions of Chrome and Chromium](https://stackoverflow.com/questions/41133391/which-chromedriver-version-is-compatible-with-which-chrome-browser-version). Make sure that the version is compatible for things to work. This is also the reason why we need another chromedriver for AWS lambda - so that it matches with the version of the headless Chromium passed to AWS lambda.

    * Headless chrome version: 69.0.3497.81
    * Chromedriver version: 2.43.600233
    * Platform version: Linux 5.10.25-linuxkit x86_64

2. chromedriver binary
    AWS runs on Amazon Linux OS - make sure to download the correct version of the chromedriver binary for use with AWS lambda vs locally.

3. Running headless mode locally may not work (esp. macOS)
    The current `headless-chromium` binary in `aws-deployment` is a file meant for Linux system, and cannot be executed on macOS. To run headless mode locally on macOS, just add `--headless` as an argument when initiating the chromedriver.

## AWS lambda with Docker

Since the Python program does not work with AWS Lambda, I tried to use a AWS Lambda [Docker container](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html) as well.

To test the Docker image locally:
1. Go to the project root folder.
2. Build the Docker image:
    ```
    docker build -t cruise-scraping:1.0 .
    ```
3. Run the Docker container:
    ```
    docker run -e email=<email> -e password=<password> -e delay=10 cruise-scraping:1.0
    ```
4. Send a request to the Docker container to invoke the lambda handler:
    ```
    curl -XPOST "http://localhost:8080/2015-03-31/functions/function/invocations" -d "{}"
    ```
5. Follow the steps [here](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html) to deploy to AWS. I wanted to use a public repository to save money, but apparently you can't use a public repository for a lambda function at this point in time.
    
    a. Create a new [private repository](https://ap-southeast-1.console.aws.amazon.com/ecr/repositories?region=ap-southeast-1).

    b. In your local terminal on your computer, log in to AWS ECR:
    ```
    aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <repo-uri>
    ```

    c. Tag the Docker image with your repository:
    ```
    docker tag <source-repo>:<image-tag> <AWS-repo>:<image-tag>
    ```

    d. Push the Docker image:
    ```
    docker push <AWS-repo>:<image-tag>
    ```

## Troubleshooting with Docker

1. Sometimes if you are unable to build the Docker image, try the following commands:

    a. remove dangling Docker images
    ```
    docker rm $(docker ps -qa)
    ```

    b. delete stopped containers and unneeded resources
    ```
    docker system prune -a
    ```

2. If the program is not scraping the page properly for some reason, we can try to diagnose the issue by seeing what is in the browser running in the Docker container. In the source code, I have configured the webdriver to take a screenshot of the browser when a timeout exception occurs.

    To see the screenshot, copy the screenshot from the Docker container to your local computer.

    a. Find the container ID
    ```
    docker ps
    ```

    b. Copy the screenshot locally
    ```
    docker cp <container-id>:/var/task/screenshot.png <path-to-destination-on-local-computer>
    ```

3. We can also enter the Docker container to see its contents:

    ```
    docker exec -it <container-id> /bin/bash
    ```

    and show the chrome debug logs:
    ```
    cat ../../opt/chrome_debug.log
    ```
