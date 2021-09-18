# cruise-scraping

Some simple web scraping to keep an eye on cruise prices.

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
8. When done, deactivate the virtual environment.

## How to use with AWS Lambda function

Context: We want to have **something** to run the Python script daily even if our computers are not turned on. One way to do so is to use [AWS lambda functions](https://aws.amazon.com/lambda/).

To deploy the code to AWS, we have to:

1. Create an AWS account
2. Create an AWS lambda function
3. [Deploy the code as a .zip file archive](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
    ```
    cd env/lib/python3.8/site-packages
    zip -r ../../../../aws-deployment/deployment-package.zip .

    cd ../../../..
    zip -g aws-deployment/deployment-package.zip main.py
    ```
4. Edit the Runtime settings > handlers section of the AWS lambda function to `main.lambda_handler` so that AWS lambda knows which Python function to call
5. [Add a time-based trigger for the function](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents.html)
6. [Add the chromedriver and headless chromium as a layer to the AWS lambda function](https://dev.to/awscommunity-asean/creating-an-api-that-runs-selenium-via-aws-lambda-3ck3). Download [chromedriver 2.43](https://chromedriver.storage.googleapis.com/index.html?path=2.43/) and download severless-chrome, then package them into a single zip file:
    ```
    cd aws-deployment

    curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-55/stable-headless-chromium-amazonlinux-2017-03.zip > headless-chromium.zip

    unzip headless-chromium.zip

    rm headless-chromium.zip

    zip -r chromedriver.zip chromedriver headless-chromium
    ```
7. Add the email and password variables as environment variables for the AWS lambda function.
8. Test the function.

For simplicity, the files needed for AWS deployment are saved in `/aws-deployment`.

## Caveats

1. chromedriver, Chrome and Chromium versions
    Different chromedriver versions support [different versions of Chrome and Chromium](https://stackoverflow.com/questions/41133391/which-chromedriver-version-is-compatible-with-which-chrome-browser-version). Make sure that the version is compatible for things to work. This is also the reason why we need another chromedriver for AWS lambda - so that it matches with the version of the headless Chromium passed to AWS lambda.

2. chromedriver binary
    AWS runs on Amazon Linux OS - make sure to download the correct version of the chromedriver binary for use with AWS lambda vs locally.

3. Running headless mode locally may not work (esp. macOS)
    The current `headless-chromium` binary in `aws-deployment` is a file meant for Linux system, and cannot be executed on macOS. To run headless mode locally on macOS, just add `--headless` as an argument when initiating the chromedriver.
