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
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
import pandas as pd
import time
import os
import random
import json
import concurrent.futures
import requests
from tqdm import tqdm  # Optional, for progress bar
from pymongo import MongoClient
from datetime import datetime
import gridfs


user_agents = [
    # Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/116.0.0.0 Safari/537.36",
    
    # Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/116.0",

    # macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_8) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15"
]


# Options
def setup_chrome_options():
    user_agent = random.choice(user_agents)  # Randomly select a User-Agent
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    chrome_options.add_argument('--headless')                  # No GUI
    chrome_options.add_argument('--no-sandbox')                # A security mechanism for separating running websites to avoid potential system failures.
    chrome_options.add_argument('--disable-dev-shm-usage')     # A shared memory concept that allows multiple processes to access the same data.
    return chrome_options


# intialize the webdriver
def create_webdriver():    
    chrome_options = setup_chrome_options()
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


# Modify the DataFrame to be thread-specific
def create_dataframe():
    # Define the columns for the DataFrame
    columns = ['status_id', 'text', 'datetime', 'images', 'links', 'embed_links']
    
    # Initialize an empty DataFrame with the specified columns
    return pd.DataFrame(columns=columns)


# Function to save cookies to a file
def save_cookies(wd, cookie_file='cookies.json'):
    with open(cookie_file, 'w') as file:
        json.dump(wd.get_cookies(), file)



def load_cookies(wd, cookie_file):
    # Load cookies from a file
    try:
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)
        
        # Navigate to a blank page within the domain context before adding cookies
        wd.get("https://x.com/")  # Ensure correct domain
        time.sleep(2)  # Wait for page load
        
        for cookie in cookies:
            try:
                # Adjust cookie if necessary to remove domain mismatches
                if "domain" in cookie:
                    del cookie["domain"]  # Let the browser auto-assign domain
                wd.add_cookie(cookie)
            except Exception as e:
                print(f"Failed to add cookie: {cookie['name']}. Error: {str(e)}")
        
        return True
    except FileNotFoundError:
        print("Cookies file not found.")
        return False


# Login function
def login_to_x(wd, login_email, login_username, login_password, max_retries=3, cookie_file='cookies.json'):
    
    retries = 0
    
    while retries < max_retries:
        
        if load_cookies(wd, cookie_file):
            wd.get("https://x.com")
            try:
                WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/header/div/div/div/div[1]")))
                print("Already logged in. Cookies loaded successfully.")
                return True
            except TimeoutException:
                print("Not logged in. Proceeding with the login.")
        else:
            print("No valid cookies found. Proceeding to manual login.")
            
        wd.get("https://x.com/i/flow/login")
        try:
            WebDriverWait(wd, 40).until(EC.title_contains("Log in to X"))
            
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[4]/label/div/div[2]/div/input')))
            
            # Find the email input box
            email_box = wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[4]/label/div/div[2]/div/input')     
            # Enter email 
            email_box.send_keys(login_email)
            
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]')))
            # Click on email next button
            wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]').click()
            
            try:
                # Find the username input box
                WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]/div/input')))
                username_box = wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]/div/input')
                
                # Enter username
                username_box.send_keys(login_username)
                
                # Click on username next button
                WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div/button')))
                wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div/button').click()
            
            except NoSuchElementException:
                # Handle the case when the username input box is not found
                print("Username input not required.")
            
            # Find the password input box
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input')))
            password_box = wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input')
            
            # Enter password
            password_box.send_keys(login_password)
            
            # Click on login button
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button')))
            wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button').click()
            
            time.sleep(2) # Wait for page load
            
            # After successful login, save cookies
            save_cookies(wd, cookie_file)
            
            return True
        
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Login attempt {retries + 1} failed: {str(e)}. Retrying...")
            retries += 1
            
            wd.get("about:blank") # This will go to the browser's default home page
            time.sleep(random.randint(0, 30))  # Random delay before retrying
        
    print("Login failed after maximum retries.")
    return False
    

def search_account(wd, target_account, retries=3, delay=5):   
    attempt = 0
    while attempt < retries:
        try:
            # Wait till the search icon loads
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div')))
            
            # Click on the search button
            wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div').click()
            
            # Wait till the search box loads
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div/div/div/form/div[1]/div/div/div/div/div[2]/div/input')))
            
            # Find the search input box
            search_box = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div/div/div/form/div[1]/div/div/div/div/div[2]/div/input')
            
            # Enter the target account name into the search box
            search_box.send_keys(target_account)
                    
            
            # Press Enter
            search_box.send_keys(Keys.ENTER)
            
            return True # If successful, exit the function
            
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error in search_account: {e}. Retrying... ({attempt + 1}/{retries})")
            attempt += 1
            time.sleep(delay)  # Wait before retrying
    
    print("Failed to search the account after maximum retries.")
    return False

    
def navigate_to_account_profile(wd, retries=3, delay=5):
    attempt = 0
    while attempt < retries:
        try:
            # Wait till the roles load
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]')))
            
            # Click on the people role
            wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]').click()
            
            # Wait till the accounts load
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span')))
            
            # Select the first result
            wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span').click()
            
            # Wait till the posts load
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/section/div/div/div[1]/div/div/article/div/div/div[2]/div[2]')))

            
            return True # If successful, exit the function
            
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error in navigate_to_account_profile: {e}. Retrying... ({attempt + 1}/{retries})")
            attempt += 1
            time.sleep(delay)  # Wait before retrying
    
    print("Failed to navigate to the account profile after maximum retries.")
    return False

def scrape(html_content):
    
    # Import HTML to python
    soup = BeautifulSoup(html_content, 'lxml')

    # Scraping post text
    post_text_div = soup.find('div', class_ = 'css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-1inkyih r-16dba41 r-bnwqim r-135wba7')
    post_text = post_text_div.text.strip() if post_text_div else None

    # Scraping post datetime
    post_datetime_div = soup.find('a', class_ = 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3 r-xoduu5 r-1q142lx r-1w6e6rj r-9aw3ui r-3s2u2q r-1loqt21')
    post_datetime = post_datetime_div.text if post_datetime_div else None

    # Scraping the images
    post_images_div = soup.find_all('img', {'alt': 'Image'})
    
    # Extract the src attribute, which contains the image URL
    post_images = [img['src'] for img in post_images_div]


    # Scraping links
    post_links_div = soup.find_all('a', class_='css-175oi2r r-1udh08x r-13qz1uu r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21')
    
    # Extract the href attribute from each link
    post_links = [a['href'] for a in post_links_div]


    # Scraping Embed Posts
    post_embed_links_div = soup.find_all('a', class_='css-146c3p1 r-bcqeeo r-1ttztb7 r-qvutc0 r-37j5jr r-a023e6 r-rjixqe r-16dba41 r-1loqt21')
    
    # Filter and build the list of post embed links
    post_embed_links = [
         f"https://x.com{a['href']}" for a in post_embed_links_div if '/status/' in a['href']
     ]


    scraped_data = {
             'text': post_text,
             'datetime': post_datetime,
             'images': post_images,
             'links': post_links,
             'embed_links': post_embed_links
             }
    return scraped_data


def add_to_dataframe(df, status_id, scraped_data):
    # Create a new DataFrame row with the scraped data
    new_row = pd.DataFrame({
        'status_id': [status_id],
        'text': [scraped_data['text']],
        'datetime': [scraped_data['datetime']],
        'images': [scraped_data['images']],
        'links': [scraped_data['links']],
        'embed_links': [scraped_data['embed_links']]
    })
    
    # Append the new row to the existing DataFrame
    return pd.concat([df, new_row], ignore_index=True)


def scrape_tweets(wd, df, num_tweets = 1, latest_status_id = None, max_retries=3):
    
    WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, "//article[@data-testid='tweet']")))
    
    tweets_counter = 0
    
    visited_tweets = {}
    wait = WebDriverWait(wd, 40)

    while tweets_counter < num_tweets:
        retry_counter = 0  # Initialize the retry counter
        while retry_counter < max_retries:            
            try: 
                articles = wd.find_elements(By.XPATH, "//article[@data-testid='tweet']")
                
                for i in range(len(articles)):
                    try:
                        # Re-locate the article element to avoid stale reference
                        article = WebDriverWait(wd, 40).until(EC.presence_of_element_located(
                            (By.XPATH, f"(//article[@data-testid='tweet'])[{i + 1}]")))  # Re-locate specific tweet
                        
                        # escpae pinned posts
                        try:
                            pinned = article.find_elements(By.XPATH, ".//div[contains(text(), 'Pinned')]")  # Adjust the XPath according to actual structure
                            if len(pinned) > 0:
                                continue
                        except NoSuchElementException:
                            # If the pinned element is not found, it means it's not a pinned post
                            pass
                                                
                        # Extract the status ID from the tweet URL
                        tweet_url = article.find_element(By.XPATH, ".//a[contains(@href, '/status/')]").get_attribute('href')
                        status_id = tweet_url.split('/status/')[1]
                        
                        # If the tweet is older than the latest scraped tweet, stop scraping
                        if latest_status_id and int(status_id) <= int(latest_status_id):
                            print(f"Encountered tweet {status_id} which is older or same as latest status_id {latest_status_id}. Stopping scrape.")
                            return df                        
                        
                        if visited_tweets.get(status_id):
                            continue
                        
                        # Wait until the tweet text div is clickable and then click it
                        WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, ".//div[@data-testid='tweetText']")))
                        tweet_text = article.find_element(By.XPATH, ".//div[@data-testid='tweetText']")
                        wait.until(EC.element_to_be_clickable(tweet_text))
                        
                        # tweet_text.click()
                        wd.execute_script("arguments[0].click();", tweet_text)
            
                        # Get page source and scrape data
                        tweet_text = WebDriverWait(wd, 40).until(
                            EC.visibility_of_element_located((By.XPATH, ".//div[@data-testid='tweetText']"))
                        )
                        
                        html_content = wd.page_source
                        scraped_data = scrape(html_content)
                        
                        # Add to DataFrame
                        df = add_to_dataframe(df, status_id, scraped_data)
                        
                        # Mark as visited
                        visited_tweets[status_id] = True                
                        tweets_counter += 1
                        
                        # Wait until the back button is clickable and then click it
                        WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, "//button[@data-testid='app-bar-back']")))
                        back_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='app-bar-back']")))
                        back_button.click()
                        
                        
                        if tweets_counter >= num_tweets:
                            break                
                        
                    except (StaleElementReferenceException, IndexError) as e:
                        print(f"Error occurred while processing post {i + 1}: {e}")
                        sleep_duration = random.uniform(1, 5)  # Random sleep between 1 and 5 seconds
                        print(f"Retrying after {sleep_duration} seconds...")
                        time.sleep(sleep_duration)
                        continue
                    
                break # Break the retry loop if no errors
                    
            except Exception as e:
                print(f"General error: {e}")
                retry_counter += 1
                if retry_counter >= max_retries:
                    print("Exceeded maximum retries for current operation.")
                    break  # Exit retry loop after max retries
                        
        wd.execute_script('window.scrollBy(0,500);')
        time.sleep(random.uniform(0.5, 2))  # Add random waits after scrolling
        
    return df
        


def download_images(image_urls, target_account, post_status_id, fs):
    for img_url in tqdm(image_urls, desc=f'Downloading images for {target_account}'):
        try:
            # Fetch the image content from the URL
            img_data = requests.get(img_url).content
            img_name = os.path.basename(img_url)  # Extract image filename from URL

            # Save the image to GridFS with additional metadata
            fs.put(
                img_data,
                filename=img_name,
                post_id=post_status_id,  # Store the post ID (e.g., X.com post ID or Instagram post ID)
                target=target_account,  # Store the target account name (e.g., Instagram profile name)
                platform="X.com",  # You can change this dynamically based on the platform (Instagram or X.com)
            )
            print(f"Uploaded to GridFS: {img_name}")

        except Exception as e:
            print(f"Failed to download {img_url}: {e}")




# Process an account in a separate thread
def process_account(target_account, login_email, login_username, login_password, tweets_number, db, fs):
    wd = create_webdriver()
    df = create_dataframe()

    collection = db[target_account]
    
    # Get the highest status_id from MongoDB
    latest_status_id = None
    latest_record = collection.find_one(sort=[("status_id", -1)])  # Adjusted to match your DataFrame's column name

    if latest_record:
        latest_status_id = latest_record["status_id"]
        print(f"Loaded latest status_id {latest_status_id} for {target_account} from MongoDB.")

    try:
        login_to_x(wd, login_email, login_username, login_password)

        # Search for the account with retries
        for attempt in range(3):
            if search_account(wd, target_account):
                break
            print(f"Search failed for {target_account} (Attempt {attempt + 1}/3).")
            if attempt == 2:
                return
        
        # Navigate to the account profile with retries
        for attempt in range(3):
            if navigate_to_account_profile(wd):
                break
            print(f"Navigate to profile failed for {target_account} (Attempt {attempt + 1}/3).")
            login_to_x(wd, login_email, login_username, login_password)
            if attempt == 2:
                return

        # Scrape tweets, stopping at the latest status_id
        df = scrape_tweets(wd, df, tweets_number, latest_status_id)
        
        if not df.empty:
            for index, row in df.iterrows():
                post_data = {
                    "account": target_account,
                    "tweet": row['text'],
                    "status_id": row['status_id'],
                    "timestamp": row['datetime'],  # Adjust this to match your DataFrame column name
                    "images": row['images'],
                    "links": row['links'],  # Include links if applicable
                    "embed_links": row['embed_links'],  # Include embed_links if applicable
                    "platform": "X.com"
                }
                
                # Upsert to avoid duplicates
                collection.update_one(
                    {"status_id": row['status_id'], "platform": "X.com"},
                    {"$set": post_data},
                    upsert=True
                )
                
                # Download images for each post if they exist
                image_urls = row.get('images')
                if image_urls:
                    download_images(image_urls, target_account, row['status_id'] ,fs)  # Adjust this call if necessary for GridFS
                
            print(f"Scraping and data save completed for {target_account}.")
        else:
            print(f"No new tweets found for {target_account}.")

    finally:
        wd.quit()


# Main function to start threading
def main():
    
    login_email = 'socialmediascrape@gmail.com'
    login_username = '@socialmedi51534'
    login_password = 'thisis_B0T'
    
    target_accounts = ['kylian mbappe', 'Cristiano Ronaldo', 'Kevin De Bruyne', 'Zlatan Ibrahimovic', 'Neymar Jr', 'Vini Jr.', 'Bill Gates', 'Elon Musk', 'Donald Trump', 'Barack Obama', 'Fox News', 'ABC News']
    
    tweets_number = 5

    client = MongoClient("mongodb://mongo:27017/")
    db = client['scraped_data_db']
    fs = gridfs.GridFS(db)


    # Set the maximum number of concurrent threads
    max_threads = 4
    
    # Use ThreadPoolExecutor to limit the number of threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        
        # Submit tasks to the executor
        for account in target_accounts:
            # Schedule the account processing to be executed
            futures.append(executor.submit(process_account, account, login_email, login_username, login_password, tweets_number, db, fs))
        
        # Optionally wait for all threads to complete
        concurrent.futures.wait(futures)
        
    print("Scraping completed for all accounts.")
    
if __name__ == "__main__":
    main()





