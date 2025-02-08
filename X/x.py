import asyncio
import os
import aiohttp
import gridfs
from urllib.parse import urlparse
from playwright.async_api import async_playwright, BrowserContext
from pymongo import MongoClient
import random
import json
import pandas as pd
import time

client = MongoClient('mongodb://localhost:27017')
db = client['scraped_data_db']
fs = gridfs.GridFS(db)

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

async def download_image_to_mongodb(image_url, post_id, username):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    img_data = await response.read()
                    img_name = f"{username}_{post_id}_{image_url.split('/')[-1]}"
                    file_id = fs.put(
                        img_data,
                        filename=img_name,
                        post_id=post_id,
                        target=username,
                        platform="X.com"
                    )
                    print(f"Image saved to MongoDB with file_id: {file_id}")
                else:
                    print(f"Failed to download {image_url} (Status: {response.status})")
    except Exception as e:
        print(f"Error downloading image {image_url}: {str(e)}")

def add_to_dataframe(df, status_id, scraped_data):
    new_row = pd.DataFrame({
        'status_id': [status_id],
        'text': [scraped_data['text']],
        'datetime': [scraped_data['datetime']],
        'images': [scraped_data['images']],
        'links': [scraped_data['links']],
        'embed_links': [scraped_data['embed_links']]
    })
    return pd.concat([df, new_row], ignore_index=True)

async def scrape_tweets(page, df, num_tweets=10, latest_status_id=None, max_retries=3):
    tweets_counter = 0
    visited_tweets = {}

    while tweets_counter < num_tweets:
        retry_counter = 0  # Initialize the retry counter
        while retry_counter < max_retries:
            try:
                articles = await page.query_selector_all("article[data-testid='tweet']")
                
                for i in range(len(articles)):
                    try:
                        # Re-locate the article element to avoid stale reference
                        article = articles[i]
                        
                        # Escape pinned posts
                        pinned = await article.query_selector("div:has-text('Pinned')")
                        if pinned:
                            continue
                        
                        # Extract the status ID from the tweet URL
                        tweet_url_element = await article.query_selector("a[href*='/status/']")
                        tweet_url = await tweet_url_element.get_attribute('href')
                        status_id = tweet_url.split('/status/')[1]
                        
                        # If the tweet is older than the latest scraped tweet, stop scraping
                        if latest_status_id and int(status_id) <= int(latest_status_id):
                            print(f"Encountered tweet {status_id} which is older or same as latest status_id {latest_status_id}. Stopping scrape.")
                            return df
                        
                        if visited_tweets.get(status_id):
                            continue
                        
                        # Wait until the tweet text div is visible
                        tweet_text_element = await article.query_selector("div[data-testid='tweetText']")
                        tweet_text = await tweet_text_element.inner_text() if tweet_text_element else None
                        
                        tweet_datetime_element = await article.query_selector("time")
                        tweet_datetime = await tweet_datetime_element.get_attribute('datetime') if tweet_datetime_element else None
                        
                        # Filter out profile images and only scrape images that are part of the tweet content
                        tweet_images_elements = await article.query_selector_all("div[data-testid='tweetPhoto'] img")
                        tweet_images = [await img.get_attribute('src') for img in tweet_images_elements if "blob:" not in await img.get_attribute('src')]
                        
                        scraped_data = {
                            'text': tweet_text,
                            'datetime': tweet_datetime,
                            'images': tweet_images,
                            'links': [],  # Add logic to extract links if needed
                            'embed_links': []  # Add logic to extract embed links if needed
                        }
                        
                        # Add to DataFrame
                        df = add_to_dataframe(df, status_id, scraped_data)
                        
                        # Mark as visited
                        visited_tweets[status_id] = True
                        tweets_counter += 1
                        
                        if tweets_counter >= num_tweets:
                            break
                
                    except Exception as e:
                        print(f"Error occurred while processing post {i + 1}: {e}")
                        sleep_duration = random.uniform(1, 5)  # Random sleep between 1 and 5 seconds
                        print(f"Retrying after {sleep_duration} seconds...")
                        await asyncio.sleep(sleep_duration)
                        continue
                
                break  # Break the retry loop if no errors
            
            except Exception as e:
                print(f"General error: {e}")
                retry_counter += 1
                if retry_counter >= max_retries:
                    print("Exceeded maximum retries for current operation.")
                    break  # Exit retry loop after max retries
        
        await page.evaluate('window.scrollBy(0, 500);')
        await asyncio.sleep(random.uniform(0.5, 2))  # Add random waits after scrolling
    
    return df

async def scrape_profile(context: BrowserContext, profile_link: str, post_limit: int = 10):
    page = await context.new_page()
    username = urlparse(profile_link).path.strip('/')

    collection = db[username]
    latest_post = collection.find_one({}, sort=[('datetime', -1)])
    latest_post_id = latest_post['post_id'] if latest_post else None
    print(f"Latest post ID in DB for {username}: {latest_post_id}")

    df = pd.DataFrame(columns=['status_id', 'text', 'datetime', 'images', 'links', 'embed_links'])

    try:
        await page.goto(profile_link)
        await page.wait_for_selector('article', timeout=10000)

        df = await scrape_tweets(page, df, num_tweets=post_limit, latest_status_id=latest_post_id)

        if not df.empty:
            for index, row in df.iterrows():
                post_data = {
                    'post_id': row['status_id'],
                    'text': row['text'],
                    'datetime': row['datetime'],
                    'image_urls': row['images'],
                    'links': row['links'],
                    'embed_links': row['embed_links']
                }

                collection.update_one(
                    {'post_id': row['status_id']},
                    {'$set': post_data},
                    upsert=True
                )
                print(f"Saved post {row['status_id']} to MongoDB for {username}")

                if row['images']:
                    for img_url in row['images']:
                        await download_image_to_mongodb(img_url, row['status_id'], username)

    except Exception as e:
        print(f"Error scraping profile {profile_link}: {str(e)}")
    finally:
        if not page.is_closed():
            await page.close()

async def scrape_profiles_concurrently(context: BrowserContext, profile_links: list, post_limit: int = 10, max_tasks: int = 4):
    semaphore = asyncio.Semaphore(max_tasks)

    async def scrape_with_limit(profile):
        async with semaphore:
            await scrape_profile(context, profile, post_limit)

    tasks = [scrape_with_limit(profile) for profile in profile_links]
    await asyncio.gather(*tasks)

async def login_to_x(username: str, password: str, browser) -> BrowserContext:
    context = await browser.new_context()
    page = await context.new_page()
    
    # Load cookies if available
    cookies_file = 'cookies.json'
    if os.path.exists(cookies_file):
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
            await context.add_cookies(cookies)
        await page.goto("https://x.com/home")
        if await page.query_selector('nav[aria-label="Primary"]'):
            print("Already logged in. Cookies loaded successfully.")
            return context

    # Perform login if cookies are not available or invalid
    await page.goto("https://x.com/i/flow/login")
    await page.fill('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[4]/label/div/div[1]', username)
    await page.click('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/button[2]/div')  # Click the "Next" button after entering the username
    
    # Check if email input field appears
    try:
        await page.wait_for_selector('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]', timeout=5000)
        await page.fill('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div[1]/div/div[2]/label/div/div[2]', 'socialmediascrape@gmail.com')
        await page.click('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div/button/div')  # Click the "Next" button after entering the email
    except Exception:
        pass  # Email input field did not appear, proceed to password

    await page.fill('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div[1]/div/div/div[3]/div/label/div/div[2]', password)
    await page.click('//html/body/div/div/div/div[1]/div/div/div/div/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/button/div')  # Click the login button after entering the password
    
    await page.wait_for_selector('nav[aria-label="Primary"]', timeout=10000)
    print("Login successful")
    
    # Save cookies
    cookies = await context.cookies()
    with open(cookies_file, 'w') as f:
        json.dump(cookies, f)
    
    return context

async def main():
    username = "@socialmedi51534"
    password = "thisis_B0T"
    profile_links = [
        "https://x.com/elonmusk",
        "https://x.com/billgates",
        "https://x.com/Cristiano",
        "https://x.com/KMbappe",
        "https://x.com/ErlingHaaland",
        "https://x.com/realDonaldTrump",
        "https://x.com/BarackObama"
        # Add more profiles as needed
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await login_to_x(username, password, browser)
        if context:
            await scrape_profiles_concurrently(context, profile_links)
            await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())