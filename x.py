#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 24 09:56:00 2024

@author: ahmeds
"""

# Importing Libraries
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time

# Options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')                # A security mechanism for separating running websites to avoid potential system failures.
chrome_options.add_argument('--disable-dev-shm-usage')     # A shared memory concept that allows multiple processes to access the same data.

# Creating WebDriver instance
wd = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=chrome_options)

# Get the main page
wd.get("https://x.com/i/flow/login")

time.sleep(3)
# Assertion statement
assert "Log in to X" in wd.title


# Fill the below account details used to login to X.com
login_email = 'socialmediascrape@gmail.com'
login_username = '@socialmedi51534'
login_password = 'thisis_B0T'

# Account to scrape
target_account = 'Bill Gates'

# Specify the path to the ChromeDriver
#chrome_driver_path = '/home/ahmeds/Downloads/chromedriver-linux64/chromedriver'

# Create a Service object
#service = Service(executable_path=chrome_driver_path)

# Initialize the Chrome browser with the Service object
#driver = webdriver.Chrome(service=service)

# Open a X.com login page
#driver.get("https://x.com/i/flow/login")

# Wait to ensure login page is fully loaded
time.sleep(5)

# Find the email input box
email_box = wd.find_element(By.XPATH, '//*[@id="layers"]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[4]/label/div/div[2]/div/input')
 
# Enter email 
email_box.send_keys(login_email)
time.sleep(1)

# Click on email next button
email_next_button = wd.find_element(By.XPATH, '//*[@id="layers"]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]').click()
time.sleep(3)

# Find the username input box
username_box = wd.find_element(By.XPATH, '//*[@id="layers"]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]/div/input')

# Enter username
username_box.send_keys(login_username)
time.sleep(1)

# Click on username next button
email_next_button = wd.find_element(By.XPATH, '//*[@id="layers"]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div/button').click()
time.sleep(5)

# Find the password input box
password_box = wd.find_element(By.XPATH, '//*[@id="layers"]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input')

# Enter password
password_box.send_keys(login_password)
time.sleep(1)

# Click on login button
login_next_button = wd.find_element(By.XPATH, '//*[@id="layers"]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button').click()

# Wait till the search icon loads
WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div')))

# Click on the search button
login_next_button = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div').click()

# Wait till the search box loads
WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div/div/div/form/div[1]/div/div/div/div/div[2]/div/input')))

# Find the search input box
search_box = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div/div/div/form/div[1]/div/div/div/div/div[2]/div/input')

# Enter the target account name to the search box
search_box.send_keys(target_account)

# Press Enter
search_box.send_keys(Keys().ENTER)

# Wait till the roles load
WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]')))

# Click on the people role
people_role = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]').click()

# Wait till the accounts loads
WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span')))

# Select the first result
account = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span').click()

# Wait till the posts load
WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/section/div/div/div[1]/div/div/article/div/div/div[2]/div[2]')))


# Import HTML to python
soup = BeautifulSoup(wd.page_source, 'lxml')

# Get all the posts
posts = soup.find_all('div', class_ = 'css-146c3p1 r-8akbws r-krxsd3 r-dnmrzs r-1udh08x r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-bnwqim')


tweets = []

# Scroling and savaing the text of the latest 200 unique tweets
while True:
    for post in posts:
        tweets.append(post.text)
    wd.execute_script('window.scrollTo(0,document.body.scrollHeight)')    
    time.sleep(3)
    soup = BeautifulSoup(wd.page_source, 'lxml')
    posts = soup.find_all('div', class_ = 'css-146c3p1 r-8akbws r-krxsd3 r-dnmrzs r-1udh08x r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-bnwqim')
    unique_tweets = list(set(tweets))
    if len(unique_tweets) > 200:
        break
    
# next steps
# - Arrange the tweets from latest to oldest
# - Make sure you scrape the full text "see more"
# - Scrape the other attributes of the post
# - How to make the web app
# - The data-base needed
  
