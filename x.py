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
login_email = ''
login_username = ''
login_password = ''

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


# # Import HTML to python
# soup = BeautifulSoup(wd.page_source, 'lxml')

# # Get all the posts
# posts = soup.find_all('div', class_ = 'css-146c3p1 r-8akbws r-krxsd3 r-dnmrzs r-1udh08x r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-bnwqim')


# # Click on the post on the page
# post = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/section/div/div/div[1]').click()

# time.sleep(1)

# # Import HTML to python
# soup = BeautifulSoup(wd.page_source, 'lxml')

# # Scraping post text
# post_text = soup.find('div', class_ = 'css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-1inkyih r-16dba41 r-bnwqim r-135wba7')
# post_text.text

# # Scraping post datetime
# post_datetime = soup.find('a', class_ = 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3 r-xoduu5 r-1q142lx r-1w6e6rj r-9aw3ui r-3s2u2q r-1loqt21')
# post_datetime.text

# # Scraping the images
# post_images_div = soup.find_all('img', {'alt': 'Image'})

# # Extract the src attribute, which contains the image URL
# post_images = [img['src'] for img in post_images_div]

# # Now `image_urls` will contain the list of image URLs from tweets
# print(post_images)


# # Scraping links
# # Find all <a> tags with the specific class
# post_links_div = soup.find_all('a', class_='css-175oi2r r-1udh08x r-13qz1uu r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21')

# # Extract the href attribute from each link
# post_links = [a['href'] for a in post_links_div]

# # Print the extracted links
# print(post_links)


# # Scraping Embed Posts
# # Find all <a> tags with the specific class
# post_embed_links_div = soup.find_all('a', class_='css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-1loqt21')

# # Filter and build the list of post embed links
# post_embed_links = [
#     f"https://x.com{a['href']}" for a in post_embed_links_div if '/status/' in a['href']
# ]

# # Print the extracted links
# print(post_embed_links)


# # Click back
# post = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div[1]/div/div[1]/div[1]/div/div/div/div/div/div[1]/button').click()
# time.sleep(1)



# posts = []

# post = {
#         'text': post_text,
#         'datetime': post_datetime,
#         'images': post_images,
#         'links': post_links,
#         'Embedtweets': post_embed_links
#         }

articles = wd.find_elements(By.XPATH, "//article[@data-testid='tweet']")

print(len(articles))
tweets  = 0

while True:
    for i in range(len(articles)):
        try:
            # Relocate the elements to avoid stale element reference
            articles = wd.find_elements(By.XPATH, "//article[@data-testid='tweet']")
            
            print(f"Clicking on post {i + 1}")
            
            # Find the specific tweet text div within the article
            post = articles[i].find_element(By.XPATH, ".//div[@data-testid='tweetText']").click()
            
            time.sleep(2)
            # More Operations
            
            tweets += 1

            # Click back
            back = wd.find_element(By.XPATH, "//button[@data-testid='app-bar-back']").click()
            time.sleep(2)
            
        except Exception as e:
            print(f"Error occurred while processing post {i + 1}: {e}")
            
    if tweets > 100:
        break
       
    wd.execute_script('window.scrollBy(0,document.body.scrollHeight);')
    time.sleep(3)
    articles = wd.find_elements(By.XPATH,"//article[@data-testid='tweet']")
    print(f"articles length now is {len(articles)}")
    time.sleep(1)

#tweets = []

# Scroling and savaing the text of the latest 200 unique tweets
#while True:
#    for post in posts:
#        tweets.append(post.text)
#    wd.execute_script('window.scrollTo(0,document.body.scrollHeight)')    
#    time.sleep(3)
#    soup = BeautifulSoup(wd.page_source, 'lxml')
#    posts = soup.find_all('div', class_ = 'css-146c3p1 r-8akbws r-krxsd3 r-dnmrzs r-1udh08x r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-bnwqim')
#    unique_tweets = list(set(tweets))
#    if len(unique_tweets) > 200:
#        break
    
# next steps
# - Arrange the tweets from latest to oldest
# - Make sure you scrape the full text "see more"
# - Scrape the other attributes of the post
# - How to make the web app
# - The data-base needed
  
