import asyncio
import os
import aiohttp
import aiofiles
import gridfs
from urllib.parse import urlparse
from playwright.async_api import async_playwright, BrowserContext
from pymongo import MongoClient
import datetime
import random  # Add this import at the top of your file if not already present


#client = MongoClient('mongodb://mongo:27017')
client = MongoClient('mongodb://localhost:27017')
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
        await page.wait_for_selector('div._aear', timeout=15000)

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
                    await page.wait_for_selector('div._aear', timeout=15000)
                else:
                    print(f"No 'Next' button found for {username} while skipping pinned posts.")
                continue

            # Stop scraping if the post ID already exists in the database
            if post_id == latest_post_id:
                print(f"Post ID {post_id} matches the latest post in DB for {username}. Stopping further scraping.")
                break

            post_caption = await page.query_selector('div._aear h1')
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
                    await page.wait_for_selector('div._aear', timeout=15000)
                    break
                retry_count += 1
                print(f"Retry {retry_count} failed to find the next post for {username}.")
            
            if retry_count == 3 or scraped_post_count >= post_limit:
                print(f"No more posts or post limit reached for {username}.")
                break

    except Exception as e:
        print(f"Error scraping profile {profile_link}: {str(e)}")
    finally:
        try:
            # Try to click any close button if present
            close_button = await page.query_selector('svg[aria-label="Close"]')
            if close_button:
                await close_button.click()
                await page.wait_for_timeout(1000)
        except:
            pass
        
        # Always close the page
        await page.close()


async def download_story_media(url, username, story_id):
    """Download media file from URL and save to local file system"""
    if not url:
        return None
        
    # Create directory for downloads if it doesn't exist
    os.makedirs(f"story_media/{username}", exist_ok=True)
    
    # Handle srcset format (pick highest quality)
    if "," in url:
        parts = url.split(",")
        url = parts[0].strip().split(" ")[0]
    
    # Determine file extension from URL or default to jpg
    file_ext = "jpg"
    if ".mp4" in url or "/mp4" in url:
        file_ext = "mp4"
    elif ".webp" in url:
        file_ext = "webp"
        
    file_path = f"story_media/{username}/{story_id}.{file_ext}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(await response.read())
                    print(f"Downloaded media to {file_path}")
                    return file_path
                else:
                    print(f"Failed to download media: HTTP {response.status}")
                    return None
    except Exception as e:
        print(f"Error downloading media: {str(e)}")
        return None

async def scrape_stories(context: BrowserContext, username: str):
    # Create a fresh page for each target
    page = await context.new_page()
    collection = db[f"{username}_stories"]
    
    try:
        # Go directly to the target URL
        print(f"Navigating to stories for {username}")
        target_url = f"https://www.instagram.com/stories/{username}/"
        await page.goto(target_url, wait_until="networkidle")
        
        # Verify we're on the correct page
        current_url = page.url
        if username not in current_url:
            print(f"Warning: URL doesn't contain target username. Expected '{username}', got URL: {current_url}")
        
        await page.wait_for_timeout(3000)
        
        # Handle the "View story" confirmation prompt
        try:
            view_story_button = await page.wait_for_selector(
                'div[role="button"]:has-text("View story"), div[role="button"]:has-text("View Story")', 
                timeout=5000
            )
            if view_story_button:
                print(f"Found 'View story' prompt for {username}, clicking to continue...")
                await view_story_button.click()
                await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"No 'View story' prompt found or error handling it: {str(e)}")
        
        # Take a debug screenshot
        os.makedirs("debug_screenshots", exist_ok=True)
        await page.screenshot(path=f"debug_screenshots/{username}_after_view_click.png", timeout=5000)
        
        # Check for story existence
        story_exists = False
        for selector in [
            'div.x5yr21d.x1n2onr6.xh8yej3 img.xl1xv1r',
            'div.x5yr21d.x1n2onr6.xh8yej3 > img',
            'video[playsinline]'  # Add video selector
        ]:
            element = await page.query_selector(selector)
            if element:
                story_exists = True
                print(f"Found story indicator: {selector}")
                break
        
        if not story_exists:
            print(f"No active stories for {username}")
            return []
            
        print(f"Found stories for {username}, attempting to extract")
        
        stories_data = []
        has_more_stories = True
        story_count = 0
        max_time = 120  # Maximum 2 minutes to avoid getting stuck
        start_time = datetime.datetime.now()
        consecutive_video_errors = 0  # Track consecutive video errors
        
        while has_more_stories and story_count < 30:
            # Time-based safety exit
            if (datetime.datetime.now() - start_time).total_seconds() > max_time:
                print(f"Safety timeout reached (2 minutes). Stopping story extraction.")
                break
                
            # URL-based safety check - make sure we're still on the target's stories
            current_url = page.url
            if f"instagram.com/stories/{username}" not in current_url:
                print(f"Navigation detected to page outside target stories: {current_url}")
                print("Stopping story extraction.")
                break
            
            story_count += 1
            print(f"Processing story {story_count} for {username}")
            
            # Get current story timestamp and ID
            story_url = page.url
            story_id = story_url.split('/')[-2] if '/stories/' in story_url else f"{username}_story_{story_count}"
            
            # Create basic story data
            story_data = {
                'story_id': story_id,
                'username': username,
                'scraped_at': datetime.datetime.now().isoformat()
            }
            
            # Check for video playback error immediately
            try:
                video_error = await page.query_selector_all('text="Sorry, We\'re having trouble playing this video."')
                if video_error and len(video_error) > 0:
                    print("Detected video playback error - this is a video story with issues")
                    story_data['media_type'] = 'video'
                    story_data['playback_error'] = True
                    consecutive_video_errors += 1
                    
                    # If we encounter too many consecutive video errors, break out
                    if consecutive_video_errors >= 3:
                        print("Too many consecutive video errors. Stopping extraction.")
                        break
                else:
                    consecutive_video_errors = 0  # Reset if no error
            except Exception as e:
                print(f"Error checking for video playback issues: {e}")
            
            # Take screenshot of whatever is visible
            os.makedirs("story_screenshots", exist_ok=True)
            story_screenshot_path = f"story_screenshots/{username}_{story_count}.png"
            await page.screenshot(path=story_screenshot_path, timeout=5000)
            story_data['screenshot_path'] = story_screenshot_path
            
            # Try to detect if this is an image or video story
            image_element = await page.query_selector('div.x5yr21d.x1n2onr6.xh8yej3 > img.xl1xv1r')
            video_element = await page.query_selector('video[playsinline]')
            
            # Initialize media variables
            media_url = None
            media_type = None
            
            # Extract media URL based on type
            if image_element:
                media_url = await image_element.get_attribute('src')
                alt_text = await image_element.get_attribute('alt')
                media_type = 'image'
                
                if media_url and "instagram" in media_url:
                    print(f"Found image story: {media_url[:50]}...")
                    if alt_text:
                        story_data['media_alt'] = alt_text
            
            elif video_element:
                # Try to get video source
                source_element = await video_element.query_selector('source')
                if source_element:
                    media_url = await source_element.get_attribute('src')
                else:
                    media_url = await video_element.get_attribute('src')
                
                media_type = 'video'
                if media_url:
                    print(f"Found video story: {media_url[:50]}...")
            
            # If we found a media URL, attempt to download it
            if media_url and "instagram" in media_url:
                story_data['media_url'] = media_url
                story_data['media_type'] = media_type
                
                # Download the media
                media_file_path = await download_story_media(media_url, username, story_id)
                
                if media_file_path:
                    story_data['media_file_path'] = media_file_path
                    print(f"Successfully downloaded {media_type} to {media_file_path}")
            else:
                print(f"Could not extract media URL from story {story_count}")
            
            # Save story data to MongoDB
            collection.update_one({'story_id': story_id}, {'$set': story_data}, upsert=True)
            stories_data.append(story_data)
            
            # Set a timeout for navigation to ensure we don't get stuck
            navigation_timeout = 5000  # 5 seconds
            
            # Navigate to next story with timeout protection
            try:
                next_button = await page.query_selector('div.x6s0dn4.x78zum5.xdt5ytf.xl56j7k')
                if next_button:
                    print(f"Moving to next story for {username}")
                    # Use a Promise with timeout for navigation
                    with page.expect_navigation(timeout=navigation_timeout, wait_until="networkidle") as navigation:
                        await next_button.click()
                    
                    # Check if navigation was successful
                    if not navigation.value:
                        print("Navigation timed out. Forcing exit from story view.")
                        break
                    
                    # Check if we're still on target user's stories after clicking next
                    new_url = page.url
                    if username not in new_url:
                        print(f"Next button navigated to a different user's stories: {new_url}")
                        print("Stopping story extraction.")
                        break
                else:
                    print(f"No more stories for {username} after {story_count}")
                    has_more_stories = False
            except Exception as e:
                print(f"Error during navigation: {e}")
                # Handle video playback errors specifically
                if "trouble playing this video" in str(e):
                    print("Detected video playback issue during navigation. Attempting to continue...")
                    try:
                        # Try clicking anywhere to dismiss the error
                        await page.mouse.click(300, 300)
                        await page.wait_for_timeout(1000)
                        
                        # Try next button again
                        next_button = await page.query_selector('div.x6s0dn4.x78zum5.xdt5ytf.xl56j7k')
                        if next_button:
                            await next_button.click()
                            await page.wait_for_timeout(2000)
                        else:
                            # If no next button, we're likely at the end
                            has_more_stories = False
                    except:
                        # If recovery fails, exit gracefully
                        print("Failed to recover from video playback error. Exiting.")
                        break
                else:
                    # For non-video errors, just break the loop
                    print("Navigation error, stopping story extraction.")
                    break
            
        return stories_data
        
    except Exception as e:
        print(f"Error scraping stories for {username}: {str(e)}")
        return []
    finally:
        try:
            # IMPORTANT: Actively try to close the story viewer
            print("Attempting to close any open story viewers...")
            
            # Try multiple ways to close/exit the story viewer
            for selector in [
                'svg[aria-label="Close"]',               # Standard close button
                'button[aria-label="Close"]',            # Alternative close button
                'div[role="button"][aria-label="Close"]' # Another possible close button format
            ]:
                try:
                    close_button = await page.query_selector(selector)
                    if close_button:
                        print(f"Found close button with selector: {selector}")
                        await close_button.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue
                    
            # Force navigation away from stories
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            print("Navigated to Instagram home page to ensure clean exit")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Always close the page
        await page.close()
        print("Page closed successfully")


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

    # Select a random profile from the list
    random_profile = random.choice(profile_links)
    random_username = urlparse(random_profile).path.strip('/')
    
    print(f"\n{'='*50}\nRANDOMLY SELECTED TARGET: {random_username}\n{'='*50}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await login_to_instagram(username, password, browser)
        if context:
            # Only scrape stories for the randomly selected profile
            print(f"\n{'='*50}\nStarting story scraping for: {random_username}\n{'='*50}\n")
            
            # Scrape stories for the random target
            await scrape_stories(context, random_username)
            
            print(f"\n{'='*50}\nCompleted story scraping for: {random_username}\n{'='*50}\n")
            
            await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
