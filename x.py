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
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
import threading
import os
import random


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


# Login function
def login_to_x(wd, login_email, login_username, login_password, max_retries=3):
    
    retries = 0
    
    while retries < max_retries:
        time.sleep(random.randint(0, 60))
        try:
            wd.get("https://x.com/i/flow/login")
            #wd.get("https://x.com")
            
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
                pass # Do nothing and continue with the rest of the code
            
            # Find the password input box
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input')))
            password_box = wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]/div[1]/input')
            
            # Enter password
            password_box.send_keys(login_password)
            
            # Click on login button
            WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button')))
            wd.find_element(By.XPATH, '/html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button').click()
            
            return True
        
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Login attempt {retries + 1} failed: {str(e)}. Retrying...")
            retries += 1
            
            wd.get("about:blank") # This will go to the browser's default home page
            time.sleep(random.randint(0, 60))  # Random delay before retrying
        
    print("Login failed after maximum retries.")
    return False
    

def search_account(wd, target_account):    
    # Wait till the search icon loads
    WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div')))
    
    # Click on the search button
    wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div').click()
    
    # Wait till the search box loads
    WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div/div/div/form/div[1]/div/div/div/div/div[2]/div/input')))
    
    # Find the search input box
    search_box = wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div/div/div/form/div[1]/div/div/div/div/div[2]/div/input')
    
    # Enter the target account name to the search box
    search_box.send_keys(target_account)
    
    # Press Enter
    search_box.send_keys(Keys().ENTER)

    
# Navigate to the account's profile
def navigate_to_account_profile(wd):    
    # Wait till the roles load
    WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]')))
    
    # Click on the people role
    wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]').click()
    
    # Wait till the accounts loads
    WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span')))
    
    # Select the first result
    wd.find_element(By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span').click()
    
    # Wait till the posts load
    WebDriverWait(wd, 40).until(EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div/div[2]/main/div/div/div/div/div/div[3]/div/div/section/div/div/div[1]/div/div/article/div/div/div[2]/div[2]')))



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
                    print(f"Exceeded maximum retries for current operation.")
                    break  # Exit retry loop after max retries
                        
        wd.execute_script('window.scrollBy(0,500);')
        time.sleep(random.uniform(0.5, 2))  # Add random waits after scrolling
        
    return df
        

# Process an account in a separate thread
def process_account(target_account, login_email, login_username, login_password, tweets_number, csv_path):
    wd = create_webdriver()
    df = create_dataframe()
    
    
    # Save the DataFrame to a CSV file in the archive folder
    file_name = os.path.join(csv_path, f'{target_account}_tweets.csv')
    
    # Get the highest status_id from the CSV (if it exists)
    latest_status_id = None
    
    if os.path.exists(file_name):
        try:
            existing_df = pd.read_csv(file_name)
            latest_status_id = existing_df['status_id'].max()
            print(f"Loaded latest status_id {latest_status_id} for {target_account}.")
        except Exception as e:
            print(f"Error loading existing CSV: {e}")        
    try:
        login_to_x(wd, login_email, login_username, login_password)
        search_account(wd, target_account)
        navigate_to_account_profile(wd)
        
        
        
        # Scrape tweets, but stop if the tweet's status_id is less than or equal to the latest_status_id
        df = scrape_tweets(wd, df, tweets_number, latest_status_id)
        
            
        if not df.empty:
            df_sorted = df.sort_values(by='status_id', ascending=True)
            
            # Append new tweets to the existing CSV
            if os.path.exists(file_name):
                df_sorted.to_csv(file_name, mode='a', header=False, index=False)
            else:
                df_sorted.to_csv(file_name, index=False)
                
            print(f"Scraping completed for {target_account}. New data saved to {file_name}.")
        else:
            print(f"No new tweets found for {target_account}.")
        
        
    finally:
        wd.quit()
    
    
# Main function to start threading
def main():
    
    login_email = 'socialmediascrape@gmail.com'
    login_username = '@socialmedi51534'
    login_password = 'thisis_B0T'
    
    target_accounts = ['Kylian Mbappé', 'Cristiano Ronaldo', 'Kevin De Bruyne', 'Zlatan Ibrahimovic', 'Neymar Jr', 'Vini Jr.', 'Bill Gates', 'NASA', 'Donald Trump', 'Barack Obama']
    #target_accounts = ['Kylian Mbappé', 'Cristiano Ronaldo', 'Kevin De Bruyne', 'Zlatan Ibrahimovic', 'Neymar Jr', 'Vini Jr.']
    #target_accounts = ['Kylian Mbappé']
    tweets_number = 5
    
    csv_path = r'./archive'
    if not os.path.exists(csv_path):
        os.makedirs(csv_path)
        
        
    threads = []
        
    # Start separate threads for each account
    for account in target_accounts:
        # time.sleep(random.randint(5, 25))
        thread = threading.Thread(target=process_account, args=(account, login_email, login_username, login_password, tweets_number, csv_path))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()
        
    print("Scraping completed for all accounts.")
    
if __name__ == "__main__":
    main()




