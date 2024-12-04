import asyncio
import os
import aiohttp
import gridfs
from urllib.parse import urlparse
from playwright.async_api import async_playwright, BrowserContext
from pymongo import MongoClient


client = MongoClient('mongodb://mongo:27017')
#client = MongoClient('mongodb://localhost:27017')
db = client['instagram_scraper']  # or whatever your DB name is
fs = gridfs.GridFS(db)

async def download_image_to_mongodb(image_url, post_id, username):
    try:
        # Fetch the image using aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    # Read the image content as bytes
                    img_data = await response.read()

                    # Save the image to GridFS with additional metadata
                    img_name = f"{username}_{post_id}_{image_url.split('/')[-1]}"
                    file_id = fs.put(
                        img_data,
                        filename=img_name,
                        post_id=post_id,            # Save the post ID
                        target=username,            # Save the username as target
                        platform="Instagram"        # Hardcode platform to "Instagram"
                    )
                    print(f"Image saved to MongoDB with file_id: {file_id}")
                else:
                    print(f"Failed to download {image_url} (Status: {response.status})")
    except Exception as e:
        print(f"Error downloading image {image_url}: {str(e)}")



STORAGE_FILE = "instagram_session.json"


async def login_to_instagram(username: str, password: str, browser) -> BrowserContext:
    if os.path.exists(STORAGE_FILE):
        print("Loading saved session...")
        context = await browser.new_context(storage_state=STORAGE_FILE)
    else:
        context = await browser.new_context()
        page = await context.new_page()
        
        # Go to Instagram login page
        await page.goto("https://www.instagram.com/")
        await page.wait_for_selector("input[name='username']", timeout=10000)
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        await page.click("button[type='submit']")

        try:
            # Wait for the page to load after login, or check for the "Save info" button
            await asyncio.sleep(10)
            await page.wait_for_selector("button._acan._acap._acas._aj1-._ap30", timeout=1500000)
            save_info_button = await page.query_selector("button._acan._acap._acas._aj1-._ap30")
            
            if save_info_button:
                print("Clicking on 'Save info' button...")
                await save_info_button.click()
                # Add a delay to ensure the session is saved before moving on
                await page.wait_for_timeout(2000)  # 2-second delay, adjust as necessary

            # Now check if the login was successful (check for a nav bar or some page element)
            await page.wait_for_selector("nav", timeout=15000)
            print("Login successful")

            # Save session state after successful login and button click
            await context.storage_state(path=STORAGE_FILE)
        
        except Exception as e:
            print("Login failed:", e)
            return None
    
    return context


async def scrape_profile(context: BrowserContext, profile_link: str, post_limit: int = 10):
    page = await context.new_page()
    username = urlparse(profile_link).path.strip('/')

    collection = db[username]  # Collection name (based on username)

    # Get the latest post_id from the database
    latest_post = collection.find_one({}, sort=[('datetime', -1)])
    latest_post_id = latest_post['post_id'] if latest_post else None
    print(f"Latest post ID in DB for {username}: {latest_post_id}")

    posts_data = []
    scraped_post_count = 0
    skipped_pinned_count = 0  # Counter for skipped pinned posts

    try:
        await page.goto(profile_link)
        await page.wait_for_selector("header", timeout=100000)

        try:
            await page.wait_for_selector('a[href*="/p/"], a[href*="/reel/"]', timeout=100000)
            first_post = await page.query_selector('a[href*="/p/"], a[href*="/reel/"]')
        except Exception as e:
            print("Timeout: First post not found.", str(e))
            first_post = None

        if not first_post:
            print(f"No posts found on the profile: {username}")
            return
        await first_post.click()
        await page.wait_for_selector('div._a9zs', timeout=150000)

        while scraped_post_count < post_limit:
            await asyncio.sleep(1)
            post_url = page.url
            if '/p/' in post_url:
                post_id = post_url.split('/p/')[1].split('/')[0]
            elif '/reel/' in post_url:
                post_id = post_url.split('/reel/')[1].split('/')[0]
            else:
                post_id = None

            # Locate the post container and check for pinned icon within the scope of that post
            post_container = await page.query_selector(f'a[href*="/p/{post_id}/"], a[href*="/reel/{post_id}/"]')
            if not post_container:
                print(f"Post container not found for post ID {post_id}")
                break

            # Check if the pinned icon exists inside the post container (scope limited to this post)
            pinned_icon = await post_container.query_selector('svg[aria-label="Pinned post icon"]')
            if pinned_icon:
                print(f"Skipping pinned post for {username}: {post_id}")
                skipped_pinned_count += 1

                # If too many posts are skipped, exit to avoid infinite loop
                if skipped_pinned_count > 10:  # Adjust the threshold if necessary
                    print(f"Too many pinned posts for {username}, exiting.")
                    break

                # Move to the next post
                next_button = await page.query_selector('svg[aria-label="Next"]')
                if next_button:
                    await next_button.click()
                    await page.wait_for_selector('div._a9zs', timeout=15000)
                else:
                    print(f"No 'Next' button found for {username} while skipping pinned posts.")
                continue

            # Stop scraping if the post ID already exists in the database
            if post_id == latest_post_id:
                print(f"Post ID {post_id} matches the latest post in DB for {username}. Stopping further scraping.")
                break

            post_caption = await page.query_selector('div._a9zs h1')
            post_datetime = await page.query_selector('time._a9ze')

            media_images = await page.locator('div._aatk img').evaluate_all(
                "elements => elements.map(el => el.src)"
            )
            image_urls = [url for url in media_images if "blob:" not in url]

            caption = await post_caption.inner_text() if post_caption else None
            datetime = await post_datetime.get_attribute('datetime') if post_datetime else None

            post_data = {
                'post_id': post_id,
                'caption': caption,
                'datetime': datetime,
                'image_urls': image_urls
            }

            # Save the post to MongoDB
            collection.update_one(
                {'post_id': post_id},  # Check for existing post by post_id
                {'$set': post_data},    # Update the post if it exists or insert it if it doesn't
                upsert=True             # Insert if the post doesn't exist
            )
            print(f"Saved post {post_id} to MongoDB for {username}")

            posts_data.append(post_data)
            scraped_post_count += 1
            skipped_pinned_count = 0  # Reset pinned counter when a valid post is scraped


            # Download images to MongoDB (if any)
            if image_urls:
                for img_url in image_urls:
                    await download_image_to_mongodb(img_url, post_id, username)

            retry_count = 0
            while retry_count < 3:
                next_button = await page.query_selector('svg[aria-label="Next"]')
                if next_button:
                    await next_button.click()
                    await page.wait_for_selector('div._a9zs', timeout=15000)
                    break
                retry_count += 1
                print(f"Retry {retry_count} failed to find the next post for {username}.")
            
            if retry_count == 3 or scraped_post_count >= post_limit:
                print(f"No more posts or post limit reached for {username}.")
                break

    except Exception as e:
        print(f"Error scraping profile {profile_link}: {str(e)}")
    finally:
        await page.close()



async def scrape_profiles_concurrently(context: BrowserContext, profile_links: list, post_limit: int = 10, max_tasks: int = 4):
    semaphore = asyncio.Semaphore(max_tasks)

    async def scrape_with_limit(profile):
        async with semaphore:
            await scrape_profile(context, profile, post_limit)

    tasks = [scrape_with_limit(profile) for profile in profile_links]
    await asyncio.gather(*tasks)


async def main():
    username = "insta.25.scra"
    password = "hello@WORLD@2025"
    profile_links = [ 
                    "https://www.instagram.com/cristiano/", # Cristiano Ronaldo 
                    "https://www.instagram.com/leomessi/", # Lionel Messi 
                    "https://www.instagram.com/neymarjr/", # Neymar Jr. 
                    "https://www.instagram.com/kyliejenner/", # Kylie Jenner 
                    "https://www.instagram.com/therock/", # Dwayne 'The Rock' Johnson 
                    "https://www.instagram.com/kimkardashian/", # Kim Kardashian 
                    "https://www.instagram.com/arianagrande/", # Ariana Grande 
                    "https://www.instagram.com/selenagomez/", # Selena Gomez 
                    "https://www.instagram.com/beyonce/", # Beyoncé 
                    "https://www.instagram.com/justinbieber/", # Justin Bieber 
                    "https://www.instagram.com/taylorswift/", # Taylor Swift 
                    "https://www.instagram.com/nike/", # Nike 
                    "https://www.instagram.com/khaby00/", # Khaby Lame 
                    "https://www.instagram.com/virat.kohli/", # Virat Kohli 
                    "https://www.instagram.com/jlo/", # Jennifer Lopez 
                    "https://www.instagram.com/iamcardib/", # Cardi B 
                    "https://www.instagram.com/kevinhart4real/", # Kevin Hart 
                    "https://www.instagram.com/kingjames/", # LeBron James 
                    "https://www.instagram.com/dualipa/", # Dua Lipa 
                    "https://www.instagram.com/eminem/", # Eminem 
                    "https://www.instagram.com/badgalriri/", # Rihanna 
                    "https://www.instagram.com/rogerfederer/", # Roger Federer 
                    "https://www.instagram.com/chrishemsworth/", # Chris Hemsworth 
                    "https://www.instagram.com/shakira/", # Shakira 
                ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await login_to_instagram(username, password, browser)
        if context:
            await scrape_profiles_concurrently(context, profile_links)
            await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
