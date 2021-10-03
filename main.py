import argparse
from bs4 import BeautifulSoup
from bs4 import Comment
import calendar
import datetime
from email.mime.text import MIMEText
import os
import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import smtplib
import sys
import time

def lambda_handler(event, context):
    main(is_running_locally=False)

def get_input_args():
    """
    Gets values of input args from the user
    """
    parser = argparse.ArgumentParser(description='Scrape cruise site and send prices to a Gmail email')
    parser.add_argument('--email', help='Gmail address, e.g. example@gmail.com', default=os.environ.get('email'))
    parser.add_argument('--password', help='Password to Gmail address', default=os.environ.get('password'))
    parser.add_argument('--delay', help='Amount of time (in seconds) to wait for webpage to load', default=os.environ.get('delay'))
    parser.add_argument('--target', help='Target class name used for checking whether page is fully loaded', default=os.environ.get('target'))
    args = parser.parse_args()

    if args.email is None:
        print('ERROR! Please provide an input email address. Use -h to see more help information.')
        sys.exit()
    
    if args.password is None:
        print('ERROR! Please provide the corresponding password to your email address. Use -h to see more help information.')
        sys.exit()
    
    if args.delay is None:
        args.delay = 10
        print(f'No delay provided by the user. Defaulting to {args.delay} seconds...')
    
    if args.target is None:
        args.target = 'cruise-list-container'
        print(f'No target provided by user. Defaulting to {args.target}...')

    return args.email, args.password, args.delay, args.target

def get_cruise_prices_html(is_running_locally, delay, target):
    """
    Gets relevant HTML from the cruise page using Selenium
    """
    if is_running_locally:
         # Use later version of Chromedriver when running locally because local version of
         # Chrome is later
        browser = webdriver.Chrome('./chromedriver')
    else:
        # Otherwise, use earlier version of Chromedriver (2.43) to match earlier version of
        # severless Chromium (matching https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-55/stable-headless-chromium-amazonlinux-2017-03.zip)
        options = Options()
        options.binary_location = '/opt/headless-chromium'

        # remove privileges from processes that do not need them so that it works with AWS Lambda
        options.add_argument('--no-sandbox')

        # run without GUI to reduce memory overhead
        options.add_argument('--headless')

        # Chrome should not use /dev/shm folder as a temp folder for internal memory management as its size is limited in Docker
        options.add_argument('--disable-dev-shm-usage')

        # counter for error message "Failed to load /opt/libosmesa.so" during init
        options.add_argument('--disable-gpu')

        # ensure that desktop site is loaded instead of mobile site etc.
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')

        # add locale so that page can load, otherwise you will see warning message "locale_file_path.empty() for locale"
        options.add_argument('--lang=en')

        # other misc settings recommended in https://stackoverflow.com/questions/60229291/aws-lambda-ruby-crawler-selenium-chrome-driver-unknown-error-unable-to-discov
        options.add_argument('--disable-application-cache') 
        options.add_argument('--disable-infobars')
        options.add_argument('--hide-scrollbars') 
        options.add_argument('--enable-logging')
        options.add_argument('--single-process')

        browser = webdriver.Chrome('/opt/chromedriver', options=options)

    # For some reason the siid is always the same
    browser.get('https://sg.dreamcruiseline.com/swift/cruise?lang=1&siid=281788&departureports=SIN&ship=14101')

    try:
        # wait for a few seconds to ensure elements by AJAX are also loaded
        element = WebDriverWait(browser, int(delay)).until(EC.presence_of_element_located((By.CLASS_NAME, f'{target}')))
    except TimeoutException:
        print(f'TimeoutException: loading the page took more than {delay} seconds!')
        browser.get_screenshot_as_file('screenshot.png')
        browser.close()
        sys.exit()

    # expand all listings
    view_all_links = browser.find_elements_by_partial_link_text('View All')
    for view_all_link in view_all_links:
        view_all_link.click()

    # get cruise sailing details
    cruise_list_container = browser.find_element_by_class_name('cruise-list-container')
    cruise_list_container_html = cruise_list_container.get_attribute('innerHTML')
    browser.close()

    return cruise_list_container_html

def get_price_table_from_html(cruise_list_container_html):
    """
    Parses HTML from the cruise page to consolidate price information into HTML tables.
    There is a table for different number of nights on the cruise
    """
    soup = BeautifulSoup(cruise_list_container_html, 'html.parser')

    # remove distracting comments in the html
    comments = soup.find_all(text=lambda text:isinstance(text, Comment))
    for comment in comments:
        comment.extract()

    cruise_item_components = soup.find_all('cruise-item-component')
    parsed_html = []
    for cruise_item_component in cruise_item_components:
        num_of_nights = cruise_item_component.select('.cruise-title > span.text-gradient')[0].get_text()
        parsed_html.append(f'<h3>{num_of_nights}</h3>')
        parsed_html.append('<table><thead><tr><th>Date</th><th>Day</th><th>Interior</th><th>Oceanview</th><th>Balcony</th><th>Suite</th></tr></thead>')
        parsed_html.append('<tbody>')
        table_rows = cruise_item_component.select('tbody > tr')
        for table_row in table_rows:
            parsed_html.append('<tr>')
            date_col = table_row.find('td', text=re.compile(r'[A-Za-z]{3}( )[0-9]{1,2}, [0-9]{4}'))
            parsed_html.append(date_col)
            day_of_week = '-'
            if date_col is not None:
                date_col_text = date_col.get_text()
                parsed_date = datetime.datetime.strptime(date_col_text.strip(), '%b %d, %Y').weekday()
                day_of_week = calendar.day_name[parsed_date][0:3]
            parsed_html.append(f'<td>{day_of_week}</td>')
            price_cols = table_row.find_all(class_='text-center')
            for price_col in price_cols:
                price = price_col.get_text()
                if price_col.find('span', {'class': 'lowest-sailing-price'}) is None:
                    parsed_html.append(f'<td>{price}</td>')
                else:
                    parsed_html.append(f'<td style="border:dashed 3px green;">{price}</td>')
            parsed_html.append('</tr>')
        parsed_html.append('</tbody></table>')

    return ''.join(str(element) for element in parsed_html)

def send_email_to_gmail(html_content, email, password):
    """
    Sends HTML content to a pre-defined Gmail account
    """
    sender = email
    receiver = email
    subject = 'Daily cruise prices update'
    message = MIMEText(html_content, 'html')
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = receiver

    gmail_user = email
    gmail_password = password

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sender, receiver, message.as_string())
        server.close()
    except Exception as e:
        print('Failed to send email: ' + repr(e))

def main(is_running_locally=True):
    print('Getting input args...')
    email, password, delay, target = get_input_args()

    print(f'Getting cruise prices HTML with delay: {delay} and target: {target}...')
    cruise_list_container_html = get_cruise_prices_html(is_running_locally, delay, target)

    print('Getting price table from HTML...')
    price_table = get_price_table_from_html(cruise_list_container_html)

    print('Sending email to Gmail...')
    send_email_to_gmail(price_table, email, password)

if __name__ == "__main__":
    main()
