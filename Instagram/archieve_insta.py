import asyncio
import os
import sys
import aiohttp
import aiofiles
import gridfs
from urllib.parse import urlparse
from playwright.async_api import async_playwright, BrowserContext
from pymongo import MongoClient
import datetime
import random  # Add this import at the top of your file if not already present
import time
from hashlib import md5


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


async def login_to_instagram(username: str, password: str, browser, context=None) -> BrowserContext:
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
            if (close_button):
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

# Modify your scrape_stories function to return status information along with data
async def scrape_stories(context: BrowserContext, username: str, start_from: int = 1):
    page = await context.new_page()
    collection = db[f"{username}_stories"]
    
    # Network request tracking setup
    network_urls = []
    seen_urls = set()
    
    async def handle_request(route):
        request = route.request
        url = request.url
        if any(ext in url for ext in ['.mp4', '.jpg', '.jpeg', 'cdninstagram']) and 'instagram' in url:
            if url not in seen_urls and not url.startswith('blob:'):
                seen_urls.add(url)
                network_urls.append({
                    'url': url,
                    'type': 'video' if any(v in url for v in ['.mp4', '/mp4']) else 'image'
                })
        await route.continue_()
    
    await page.route('**/*', handle_request)
    
    # Add this to the beginning of your scrape_stories function
    # Right after creating the page

    # Add a stronger script to try to help with video playback
    await page.add_init_script('''
        // Improved video playback support
        (() => {
            // Override video playback restrictions
            const originalPlay = HTMLVideoElement.prototype.play;
            HTMLVideoElement.prototype.play = function() {
                this.muted = true;
                this.autoplay = true;
                this.controls = false;
                this.playsInline = true;
                this.loop = true;
                
                // Force video to be visible
                const makeVideoVisible = () => {
                    this.style.visibility = 'visible';
                    this.style.opacity = '1';
                };
                
                makeVideoVisible();
                setTimeout(makeVideoVisible, 500);
                
                return originalPlay.apply(this);
            };
            
            // Auto-play videos when they're added to the DOM
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.addedNodes) {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeName === 'VIDEO') {
                                setTimeout(() => {
                                    node.muted = true;
                                    node.play().catch(e => {});
                                }, 100);
                            }
                        });
                    }
                });
            });
            
            // Start observing
            observer.observe(document.body, { childList: true, subtree: true });
            
            // Periodically try to play videos
            setInterval(() => {
                document.querySelectorAll('video').forEach(video => {
                    video.muted = true;
                    video.play().catch(e => {});
                });
            }, 1000);
        })();
    ''')

    try:
        print(f"Navigating to stories for {username}")
        
        # IMPORTANT: Go directly to stories URL
        await page.goto(f"https://www.instagram.com/stories/{username}/", wait_until="networkidle", timeout=30000)
        
        # Take debug screenshot to see initial state
        os.makedirs("debug_screenshots", exist_ok=True)
        await page.screenshot(path=f"debug_screenshots/{username}_initial_view.png")
        
        # Add more comprehensive "View story" button detection
        try:
            # Use a more broad selector that will catch different variations
            view_story_selectors = [
                'div[role="button"]:has-text("View")',  # More general
                'div[role="button"]:has-text("view")', 
                'div[role="button"]:has-text("Story")', 
                'div[role="button"]:has-text("story")',
                'div._acan._acap._acas'  # Button class pattern
            ]
            
            view_button = None
            for selector in view_story_selectors:
                try:
                    view_button = await page.wait_for_selector(selector, timeout=3000)
                    if view_button:
                        print(f"Found story prompt with selector: {selector}")
                        break
                except:
                    continue
            
            if view_button:
                print(f"Clicking 'View story' button for {username}...")
                await view_button.click()
                await page.wait_for_timeout(3000)
                
                # Take another screenshot after clicking
                await page.screenshot(path=f"debug_screenshots/{username}_after_view_click.png")
            else:
                print("No 'View story' button found, but stories might load directly")
        except Exception as e:
            print(f"Error handling story prompt: {str(e)}")
        
        # Expanded story detection with more selectors
        story_exists = False
        story_selectors = [
            'div.x5yr21d.x1n2onr6.xh8yej3 img.xl1xv1r',  # Image in story
            'video[playsinline]',  # Video element
            'div[role="button"][aria-label="Pause story"]',  # Pause button
            '.x6s0dn4.x78zum5.xdt5ytf.xl56j7k',  # Next button
            'div._ac0m',  # Story container
            'section._ab8w._ab94._ab99._ab9h._ab9m._ab9o._abcm',  # Story section
            'img[data-visualcompletion="media-vc-image"]'  # Content image
        ]
        
        for selector in story_selectors:
            element = await page.query_selector(selector)
            if element:
                story_exists = True
                print(f"Found story indicator with selector: {selector}")
                break
        
        # Even if we didn't find a specific indicator, check URL and take a final debug shot
        if not story_exists:
            current_url = page.url
            if '/stories/' in current_url:
                print("URL contains 'stories' path, attempting extraction anyway")
                await page.screenshot(path=f"debug_screenshots/{username}_url_check.png")
                story_exists = True
            else:
                print(f"No story indicators found for {username}")
                await page.screenshot(path=f"debug_screenshots/{username}_no_stories.png")
                return []
        
        print(f"Proceeding with story extraction for {username}")
        
        # Create directories
        os.makedirs("story_screenshots", exist_ok=True)
        os.makedirs(f"story_media/{username}", exist_ok=True)
        
        # Try clicking on center of screen to activate story
        try:
            # Get viewport dimensions
            viewport = await page.evaluate('''() => { 
                return {width: window.innerWidth, height: window.innerHeight} 
            }''')
            
            # Click center
            center_x = viewport['width'] / 2
            center_y = viewport['height'] / 2
            await page.mouse.click(center_x, center_y)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Error clicking center: {e}")
        
        # Rest of your story extraction code remains the same...
        stories_data = []
        story_count = start_from - 1  # Subtract 1 because we increment at the start of the loop
        max_stories = 30
        consecutive_navigation_failures = 0  # Track navigation failures separately
        consecutive_media_failures = 0       # Track media extraction failures separately
        
        # Track how long we've been on the same video story
        video_story_detection_count = 0
        last_video_story_id = None

        # Add this to track which stories we've already stored
        processed_story_ids = set()

        while story_count < max_stories and consecutive_navigation_failures < 3:
            story_count += 1
            print(f"Processing story {story_count} for {username}")
            
            # Skip if we've already processed this story
            story_id = f"{username}_story_{story_count}"
            if story_id in processed_story_ids:
                print(f"Skipping already processed story ID: {story_id}")
                continue
            processed_story_ids.add(story_id)
            
            # Take screenshot first
            story_screenshot_path = f"story_screenshots/{username}_{story_id}.png"
            await page.screenshot(path=story_screenshot_path, full_page=False)
            
            # Create basic story data
            story_data = {
                'story_id': story_id,
                'username': username,
                'scraped_at': datetime.datetime.now().isoformat(),
                'screenshot_path': story_screenshot_path
            }
            
            # Detect story type
            story_type = await detect_story_type(page)
            story_data['media_type'] = story_type
            
            # Handle different story types
            if story_type == "video":
                # Save video story data without attempting to extract media
                print(f"🎬 Detected video story - saving and navigating to next")
                
                # Save to MongoDB and add to results
                collection.update_one({'story_id': story_id}, {'$set': story_data}, upsert=True)
                stories_data.append(story_data)
                
                # Track video stories to detect being stuck
                if story_id == last_video_story_id:
                    video_story_detection_count += 1
                    print(f"⚠️ Same video story detected {video_story_detection_count} times")
                    
                    if video_story_detection_count >= 3:
                        print("🛑 Stuck on video story - ending extraction")
                        return {
                            "status": "VIDEO_STORY_BLOCKER",
                            "data": stories_data,
                            "last_processed_story": story_count
                        }
                else:
                    video_story_detection_count = 0
                    last_video_story_id = story_id
                
                # Navigate past video
                navigation_success = await navigate_story(page, "video", username, story_id)
                
            elif story_type == "image":
                # Extract image URL
                image_element = await page.query_selector('div.x5yr21d.x1n2onr6.xh8yej3 > img.xl1xv1r')
                if image_element:
                    media_url = await image_element.get_attribute('src')
                    if media_url and "instagram" in media_url:
                        story_data['media_url'] = media_url
                        
                        # Download image
                        if not media_url.startswith('blob:'):
                            media_file_path = await download_story_media(media_url, username, story_id)
                            if media_file_path:
                                story_data['media_file_path'] = media_file_path
                
                # Save to MongoDB and add to results
                collection.update_one({'story_id': story_id}, {'$set': story_data}, upsert=True)
                stories_data.append(story_data)
                
                # Navigate to next
                navigation_success = await navigate_story(page, "image", username, story_id)
            
            else:
                # Unknown type, just save screenshot and move on
                story_data['media_extraction_failed'] = True
                collection.update_one({'story_id': story_id}, {'$set': story_data}, upsert=True)
                stories_data.append(story_data)
                
                navigation_success = await navigate_story(page, "unknown", username, story_id)
            
            # Check for end of stories
            end_of_stories = await page.evaluate('''
                () => {
                    // Check for end indicators in text
                    const bodyText = document.body.innerText;
                    if (bodyText.includes("You're all caught up") || 
                        bodyText.includes("No more stories") || 
                        bodyText.includes("suggested profiles")) {
                        return true;
                    }
                    
                    // Check for suggestions grid
                    const suggestions = document.querySelectorAll('div[role="button"][tabindex="0"]');
                    if (suggestions.length > 5) {
                        return true;
                    }
                    
                    return false;
                }
            ''')
            
            if end_of_stories:
                print("🏁 Detected end of stories - exiting story loop")
                break
                
            # Track navigation failures
            if not navigation_success:
                consecutive_navigation_failures += 1
                print(f"⚠️ Navigation failure {consecutive_navigation_failures}/3")
            else:
                consecutive_navigation_failures = 0

        # At the normal end of the function, return success code
        return {
            "status": "SUCCESS",
            "data": stories_data,
            "last_processed_story": story_count
        }
    
    except Exception as e:
        print(f"Error scraping stories for {username}: {str(e)}")
        # Return a different status for general errors
        return {
            "status": "ERROR", 
            "error": str(e),
            "data": []
        }
    
    finally:
        # Clean up
        try:
            print("Cleaning up and exiting story viewer...")
            
            # Try to close the story viewer
            for selector in [
                'svg[aria-label="Close"]',
                'button[aria-label="Close"]',
                'div[role="button"][aria-label="Close"]'
            ]:
                try:
                    close_button = await page.query_selector(selector)
                    if (close_button):
                        print(f"Found close button with selector: {selector}")
                        await close_button.click()
                        await page.wait_for_timeout(1000)
                        break
                except:
                    continue
            
            # Navigate away
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            print("Navigated to Instagram home page to ensure clean exit")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        await page.close()
        print("Page closed successfully")


async def scrape_profiles_concurrently(context: BrowserContext, profile_links: list, post_limit: int = 10, max_tasks: int = 4):
    semaphore = asyncio.Semaphore(max_tasks)

    async def scrape_with_limit(profile):
        async with semaphore:
            await scrape_profile(context, profile, post_limit)

    tasks = [scrape_with_limit(profile) for profile in profile_links]
    await asyncio.gather(*tasks)


import os

async def main():
    if sys.version_info >= (3, 8):
        asyncio.get_event_loop().set_debug(True)
    # Get credentials from environment variables
    username = os.environ.get("INSTAGRAM_USERNAME", "insta.25.scra")
    password = os.environ.get("INSTAGRAM_PASSWORD", "hello@WORLD@2025")
    
    # Set these with:
    # export INSTAGRAM_USERNAME=your_username
    # export INSTAGRAM_PASSWORD=your_password
    
    profile_links = [ 
                    "https://www.instagram.com/cristiano/",
                    "https://www.instagram.com/kingjames/",
                    "https://www.instagram.com/neymarjr/",
                    "https://www.instagram.com/therock/", 
                    "https://www.instagram.com/selenagomez/",
                    "https://www.instagram.com/kyliejenner/",
                    "https://www.instagram.com/taylorswift/",
                    "https://www.instagram.com/justinbieber/",
                    "https://www.instagram.com/arianagrande/",
                    "https://www.instagram.com/dualipa/",
                    "https://www.instagram.com/iamcardib/"
                   ]

    # Select a random profile
    random_profile = random.choice(profile_links)
    random_username = urlparse("https://www.instagram.com/arianagrande/").path.strip('/')
    
    # random_username = urlparse(random_profile).path.strip('/')
    
    print(f"\n{'='*50}\nRANDOMLY SELECTED TARGET: {random_username}\n{'='*50}\n")

    async with async_playwright() as p:
        # Use the mobile settings directly on the main browser context
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--autoplay-policy=no-user-gesture-required',
                '--disable-web-security',
                '--use-fake-ui-for-media-stream',
                '--disable-features=PreloadMediaEngagementData,AutoplayIgnoreWebAudio',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # IMPORTANT: DO NOT create a context here anymore
        # Let login_to_instagram create or load the context
        
        # Get a logged-in context
        logged_in_context = await login_to_instagram(username, password, browser)
        
        if logged_in_context:
            # Verify we're logged in by checking a profile
            verify_page = await logged_in_context.new_page()
            await verify_page.goto("https://www.instagram.com/")
            await verify_page.wait_for_timeout(2000)
            
            # Check for login indicators
            is_logged_in = await verify_page.query_selector('svg[aria-label="Home"]')
            
            if not is_logged_in:
                print("WARNING: Not properly logged in. Cannot proceed with story scraping.")
                await verify_page.screenshot(path="debug_screenshots/login_verification.png")
                await verify_page.close()
                await browser.close()
                return
                
            await verify_page.close()
            
            max_retry_attempts = 3
            retry_count = 0
            last_story_num = 0  # Track the last story we successfully processed
            all_stories_data = []  # Collect all stories across retry attempts
            
            while retry_count < max_retry_attempts:
                try:
                    print(f"\n{'='*50}\nStarting story scraping for: {random_username} (Attempt {retry_count + 1})\n{'='*50}\n")
                    
                    # Start from the story after the last one we processed
                    start_from = last_story_num + 1
                    
                    # Call scrape_stories with the logged in context
                    result = await scrape_stories(logged_in_context, random_username, start_from=start_from)
                    
                    # Check the status code from the result
                    if isinstance(result, dict):  # Ensure we got a dict response
                        status = result.get("status", "UNKNOWN")
                        stories = result.get("data", [])
                        
                        # Add any new stories to our collection
                        all_stories_data.extend(stories)
                        
                        # Update our last processed story
                        if "last_processed_story" in result:
                            last_story_num = result["last_processed_story"]
                        
                        if status == "SUCCESS":
                            print(f"Successfully completed story scraping with {len(stories)} stories")
                            break  # Exit retry loop on success
                            
                        elif status == "VIDEO_STORY_BLOCKER":
                            print(f"Encountered problematic video story at position {last_story_num}")
                            print(f"Collected {len(stories)} stories before getting blocked")
                            
                            # Increment retry counter only for video story blockers
                            retry_count += 1
                            
                            # If we have a lot of stories already, consider it good enough
                            if len(all_stories_data) >= 15:
                                print("Already collected a substantial number of stories, ending gracefully")
                                break
                            
                            print(f"Will retry from story #{start_from + 1}")
                            
                            # Completely close browser and restart for a clean session
                            await browser.close()
                            browser = await p.chromium.launch(
                                headless=False,
                                args=[
                                    '--autoplay-policy=no-user-gesture-required',
                                    '--disable-web-security',
                                    '--use-fake-ui-for-media-stream',
                                    '--disable-features=PreloadMediaEngagementData,AutoplayIgnoreWebAudio',
                                    '--disable-blink-features=AutomationControlled'
                                ]
                            )
                            logged_in_context = await login_to_instagram(username, password, browser)
                            await asyncio.sleep(5)  # Give it time to stabilize
                        
                        else:  # Any other status like ERROR or UNKNOWN
                            print(f"Received status: {status}, not retrying")
                            if stories:
                                print(f"Still collected {len(stories)} stories")
                            break  # Don't retry for general errors
                
                    else:  # Legacy return format (just a list)
                        all_stories_data.extend(result if isinstance(result, list) else [])
                        print(f"Successfully scraped {len(result) if isinstance(result, list) else 0} stories")
                        break  # No need to retry
            
                except Exception as e:
                    print(f"Unexpected error during story scraping: {e}")
                    break  # Don't retry for unexpected errors
            
            print(f"\n{'='*50}\nCompleted story scraping for: {random_username} with {len(all_stories_data)} total stories\n{'='*50}\n")
            
        await browser.close()

# Add this function to your script near the beginning
async def force_next_story(page):
    """Force navigation to next story using direct DOM manipulation"""
    try:
        # 1. Try direct SVG path targeting - most precise method
        result = await page.evaluate('''
            () => {
                // Find the next button using exact SVG path - this is most reliable
                const svgPathQuery = 'path[d^="M12.005.503a11.5 11.5 0 1 0 11.5 11.5 11.513"]';
                const nextPath = document.querySelector(svgPathQuery);
                
                if (nextPath) {
                    // Walk up to find the clickable element (usually 2-3 levels up)
                    let element = nextPath;
                    let level = 0;
                    let maxLevels = 5;
                    
                    while (element && level < maxLevels) {
                        console.log(`Checking element: ${element.tagName} at level ${level}`);
                        
                        // If we find the SVG or a button/div, try clicking
                        if (element.tagName === 'svg' || 
                            element.tagName === 'BUTTON' || 
                            (element.tagName === 'DIV' && element.getAttribute('role') === 'button')) {
                            
                            console.log("Found clickable ancestor:", element.tagName);
                            
                            // Create a range of simulated click events to maximize chances
                            try {
                                // 1. Native click()
                                element.click();
                                
                                // 2. Dispatch MouseEvent
                                const rect = element.getBoundingClientRect();
                                const clickX = rect.left + rect.width/2;
                                const clickY = rect.top + rect.height/2;
                                
                                const clickEvent = new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window,
                                    clientX: clickX,
                                    clientY: clickY
                                });
                                element.dispatchEvent(clickEvent);
                                
                                // 3. Simulate complete mouse interaction sequence
                                const events = [
                                    new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window, clientX: clickX, clientY: clickY}),
                                    new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window, clientX: clickX, clientY: clickY}),
                                    new MouseEvent('click', {bubbles: true, cancelable: true, view: window, clientX: clickX, clientY: clickY})
                                ];
                                
                                events.forEach(e => element.dispatchEvent(e));
                                return {success: true, method: "direct-svg-path", element: element.tagName};
                            } catch(e) {
                                console.error("Error during click:", e);
                            }
                        }
                        
                        element = element.parentElement;
                        level++;
                    }
                }
                
                // 4. Last resort - bypass button completely and click screen edge
                const width = window.innerWidth;
                const height = window.innerHeight;
                
                // Create an array of positions to try clicking
                const positions = [
                    {x: width * 0.95, y: height * 0.5},  // Far right center
                    {x: width * 0.9, y: height * 0.3},   // Right upper
                    {x: width * 0.9, y: height * 0.7},   // Right lower
                    {x: width * 0.99, y: height * 0.5}   // Extreme right
                ];
                
                // Try clicking at each position
                for (const pos of positions) {
                    const elementAtPoint = document.elementFromPoint(pos.x, pos.y);
                    if (elementAtPoint) {
                        const clickEvent = new MouseEvent('click', {
                            bubbles: true, cancelable: true, view: window,
                            clientX: pos.x, clientY: pos.y
                        });
                        elementAtPoint.dispatchEvent(clickEvent);
                    }
                }
                
                return {success: true, method: "edge-click", positions: positions.length};
            }
        ''')
        
        print(f"Force next story result: {result}")
        return result
        
    except Exception as e:
        print(f"Error in force_next_story: {e}")
        return {"success": False, "error": str(e)}

# Add this function to your script
async def check_end_of_stories(page):
    """Check if we've reached the end of stories"""
    try:
        is_end = await page.evaluate('''
            () => {
                // 1. Check for standard end-of-stories indicators
                const endTexts = ["You're all caught up", "No more stories", "All stories viewed"];
                const bodyText = document.body.innerText;
                
                for (const text of endTexts) {
                    if (bodyText.includes(text)) {
                        return {ended: true, reason: "end-text-found", text};
                    }
                }
                
                // 2. Check for profile suggestions - indicates stories are done
                const suggestions = document.querySelectorAll('[data-testid="user-card"], div.x1ja2u2z, div.x6s0dn4.x78zum5.x1q0g3np.x1a02dak');
                if (suggestions.length > 3) {
                    return {ended: true, reason: "suggestions-found", count: suggestions.length};
                }
                
                // 3. Check if returned to main feed
                const feedIndicators = document.querySelectorAll('[aria-label="Feed"]');
                if (feedIndicators.length > 0) {
                    return {ended: true, reason: "returned-to-feed"};
                }
                
                return {ended: false};
            }
        ''')
        
        return is_end.get('ended', False)
    
    except Exception as e:
        print(f"Error checking end of stories: {e}")
        return False

# Add this improved function to navigate past video stories with the exact XPath
async def navigate_past_video_story(page):
    """Use the exact XPath of the next button to navigate past video stories"""
    try:
        print("🛑 VIDEO STORY DETECTED - Using specialized navigation")
        
        # Try exact XPath approach first - this is most reliable
        exact_xpath = '/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/section/div[1]/div/div/div[2]/div[2]/div/div/svg'
        
        # Check if the element exists before trying to click it
        button_exists = await page.evaluate(f'''
            () => {{
                const element = document.evaluate(
                    "{exact_xpath}", 
                    document,
                    null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                ).singleNodeValue;
                return element !== null;
            }}
        ''')
        
        if (button_exists):
            print("✅ Found next button using exact XPath")
            
            # Direct JavaScript click on the XPath element
            success = await page.evaluate(f'''
                () => {{
                    try {{
                        const nextButton = document.evaluate(
                            "{exact_xpath}", 
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        ).singleNodeValue;
                        
                        if (nextButton) {{
                            // Get the parent elements to find clickable ancestor
                            let clickTarget = nextButton;
                            for (let i = 0; i < 5; i++) {{
                                // Try to click at each level up
                                try {{ 
                                    clickTarget.click();
                                    console.log("Clicked element at level", i);
                                }} catch(e) {{}}
                                
                                // Also try synthetic event approach
                                const rect = clickTarget.getBoundingClientRect();
                                const clickEvent = new MouseEvent('click', {{
                                    bubbles: true,
                                    cancelable: true,
                                    view: window,
                                    clientX: rect.left + rect.width / 2,
                                    clientY: rect.top + rect.height / 2
                                }});
                                clickTarget.dispatchEvent(clickEvent);
                                
                                // Move up to parent
                                if (clickTarget.parentElement) {{
                                    clickTarget = clickTarget.parentElement;
                                }} else {{
                                    break;
                                }}
                            }}
                            return true;
                        }}
                        return false;
                    }} catch(e) {{
                        console.error("Error clicking next button:", e);
                        return false;
                    }}
                }}
            ''')
            
            if (success):
                print("✅ Successfully clicked next button with XPath")
                # Wait for navigation effects
                await page.wait_for_timeout(2000)
                return True
        
        # Fall back to keyboard navigation if direct click fails
        print("⚠️ XPath click failed, trying keyboard navigation")
        await page.keyboard.press('ArrowRight')
        await page.wait_for_timeout(2000)
        
        # Last resort - try clicking on the right edge of the screen
        print("⚠️ Trying edge click as last resort")
        viewport = await page.evaluate('() => { return {width: window.innerWidth, height: window.innerHeight} }')
        await page.mouse.click(viewport['width'] * 0.95, viewport['height'] * 0.5)
        await page.wait_for_timeout(2000)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in navigate_past_video_story: {e}")
        return False

# Add this improved function to your navigate_past_video_story function

async def navigate_past_video_story(page):
    """Use the exact parent XPath to navigate past video stories"""
    try:
        print("🎬 VIDEO STORY DETECTED - Using direct parent element navigation")
        
        # Use the exact parent element XPath (this is the clickable element we need)
        parent_xpath = '/html/body/div[1]/div/div/div[3]/div/div/div[3]/div/section/div[1]/div/div/div[2]/div[2]/div/div'
        
        # Direct attempt to click the parent element
        success = await page.evaluate(f'''
            () => {{
                try {{
                    // Use XPath to find the exact parent element
                    const nextButtonParent = document.evaluate(
                        "{parent_xpath}", 
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    ).singleNodeValue;
                    
                    if (nextButtonParent) {{
                        console.log("Found exact parent element to click");
                        
                        // 1. Direct click on the exact parent element
                        nextButtonParent.click();
                        
                        // 2. Also use synthetic events to maximize chance of success
                        const rect = nextButtonParent.getBoundingClientRect();
                        const centerX = rect.left + rect.width/2;
                        const centerY = rect.top + rect.height/2;
                        
                        // Create a precise click sequence
                        [
                            new MouseEvent('mousedown', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}}),
                            new MouseEvent('mouseup', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}}),
                            new MouseEvent('click', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}})
                        ].forEach(event => nextButtonParent.dispatchEvent(event));
                        
                        return true;
                    }} else {{
                        console.log("Could not find the exact parent element");
                    }}
                    return false;
                }} catch(e) {{
                    console.error("Error clicking next button parent:", e);
                    return false;
                }}
            }}
        ''')
        
        # Wait after the click attempt
        await page.wait_for_timeout(2000)
        
        if success:
            print("✅ Successfully clicked next button parent element")
            return True
            
        # Fallbacks if the exact parent element approach fails
        print("⚠️ Parent element click failed, trying keyboard and edge clicks...")
        
        # Try keyboard navigation
        await page.keyboard.press('ArrowRight')
        await page.wait_for_timeout(1500)
        
        # Try edge clicking as last resort
        viewport = await page.evaluate('() => { return {width: window.innerWidth, height: window.innerHeight} }')
        await page.mouse.click(viewport['width'] * 0.95, viewport['height'] * 0.5)
        await page.wait_for_timeout(1500)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in navigate_past_video_story: {e}")
        return False

async def detect_story_type(page):
    """Detect if the current story is a video, image, or other type"""
    try:
        # Check for video indicators
        video_elements = await page.query_selector_all('video, svg[aria-label="Video"], div.x78zum5 > div.x1qjc9v5')
        video_error = await page.query_selector('text="Sorry, We\'re having trouble playing this video."')
        
        if video_elements or video_error:
            return "video"
            
        # Check for image indicators
        image_element = await page.query_selector('div.x5yr21d.x1n2onr6.xh8yej3 > img.xl1xv1r, img[data-visualcompletion="media-vc-image"]')
        if image_element:
            return "image"
            
        # If no clear indicators, default to unknown
        return "unknown"
    except Exception as e:
        print(f"Error detecting story type: {e}")
        return "error"

async def navigate_story(page, story_type, username, story_id):
    """Navigate to the next story with appropriate method based on story type"""
    try:
        if story_type == "video":
            print("🎬 VIDEO STORY - Using specialized navigation")
            
            # Use the exact parent element XPath (the clickable element we need)
            parent_xpath = '/html/body/div[1]/div/div/div[3]/div/div/div[3]/div/section/div[1]/div/div/div[2]/div[2]/div/div'
            
            # Direct attempt to click the parent element
            success = await page.evaluate(f'''
                () => {{
                    try {{
                        // Find the parent element with XPath
                        const nextButtonParent = document.evaluate(
                            "{parent_xpath}", 
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        ).singleNodeValue;
                        
                        if (nextButtonParent) {{
                            console.log("Found parent element to click");
                            
                            // Direct click plus synthetic events for reliability
                            nextButtonParent.click();
                            
                            // Create a precise click sequence with coordinates
                            const rect = nextButtonParent.getBoundingClientRect();
                            const centerX = rect.left + rect.width/2;
                            const centerY = rect.top + rect.height/2;
                            
                            [
                                new MouseEvent('mousedown', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}}),
                                new MouseEvent('mouseup', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}}),
                                new MouseEvent('click', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}})
                            ].forEach(event => nextButtonParent.dispatchEvent(event));
                            
                            return true;
                        }}
                        return false;
                    }} catch(e) {{
                        console.error("Error clicking parent:", e);
                        return false;
                    }}
                }}
            ''')
            
            # Wait for navigation to take effect
            await page.wait_for_timeout(1500)
            
            # Fallbacks if exact XPath fails
            if not success:
                # Try keyboard navigation
                await page.keyboard.press('ArrowRight')
                await page.wait_for_timeout(1000)
                
                # Try clicking on edge of screen 
                viewport = await page.evaluate('() => { return {width: window.innerWidth, height: window.innerHeight} }')
                await page.mouse.click(viewport['width'] * 0.95, viewport['height'] * 0.5)
                await page.wait_for_timeout(1000)
        else:
            # For images and other types, use normal navigation
            await page.keyboard.press('ArrowRight')
            await page.wait_for_timeout(1500)
            
            # Also try clicking next button
            next_button = await page.query_selector('div.x6s0dn4.x78zum5.xdt5ytf.xl56j7k, svg[aria-label="Next"]')
            if next_button:
                await next_button.click()
                await page.wait_for_timeout(1500)
                
        return True
        
    except Exception as e:
        print(f"❌ Error in navigation: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())


