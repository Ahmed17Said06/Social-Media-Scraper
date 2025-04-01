# Instagram Story Scraper
# A tool to extract stories from Instagram accounts

import asyncio
import os
import re
import random
import datetime
import time
import sys
import json
from hashlib import md5
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple, Union
import aiohttp
import aiofiles
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from pymongo import MongoClient

# ================= DATABASE CONFIGURATION =================
# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["instagram_scraper"]
collection = db["stories"]

# ================= CONFIGURATION SETTINGS =================
# Create necessary directories
os.makedirs("story_screenshots", exist_ok=True)
os.makedirs("story_media", exist_ok=True)
os.makedirs("debug_screenshots", exist_ok=True)
os.makedirs("cookies", exist_ok=True)

# ================= HELPER FUNCTIONS =================
async def download_file(url: str, filepath: str) -> bool:
    """Download a file from URL to local path"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(await response.read())
                    return True
                else:
                    print(f"Failed to download file: {response.status}")
                    return False
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

async def download_story_media(url: str, username: str, story_id: str) -> Optional[str]:
    """Download story media and return the local file path"""
    try:
        if not url or url.startswith("blob:"):
            return None
            
        # Create media directory for user if it doesn't exist
        user_media_dir = f"story_media/{username}"
        os.makedirs(user_media_dir, exist_ok=True)
        
        # Parse URL to get file extension
        parsed_url = urlparse(url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1]
        if not ext:
            ext = ".jpg"  # Default extension
            
        # Create filename and path
        filename = f"{story_id}{ext}"
        filepath = f"{user_media_dir}/{filename}"
        
        # Download the file
        success = await download_file(url, filepath)
        if success:
            print(f"Downloaded media to {filepath}")
            return filepath
        return None
    except Exception as e:
        print(f"Error downloading story media: {e}")
        return None

# ================= INSTAGRAM AUTHENTICATION =================
STORAGE_FILE = "instagram_session.json"

async def login_to_instagram(username: str, password: str, browser: Browser) -> BrowserContext:
    """Log in to Instagram using the reliable approach from the original script"""
    print(f"Starting Instagram login for {username}...")
    
    # Use storage state if available (more reliable than cookies)
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
            await page.wait_for_selector("button._acan._acap._acas._aj1-._ap30", timeout=15000)
            save_info_button = await page.query_selector("button._acan._acap._acas._aj1-._ap30")
            
            if save_info_button:
                print("Clicking on 'Save info' button...")
                await save_info_button.click()
                # Add a delay to ensure the session is saved before moving on
                await page.wait_for_timeout(2000)

            # Now check if the login was successful (check for a nav bar or some page element)
            await page.wait_for_selector("nav", timeout=15000)
            print("Login successful")

            # Save session state after successful login and button click
            await context.storage_state(path=STORAGE_FILE)
        
        except Exception as e:
            print("Login failed:", e)
            await page.screenshot(path="debug_screenshots/login_failed.png")
            await context.close()
            raise Exception(f"Login failed: {e}")
    
    # Verify login with a test page
    verify_page = await context.new_page()
    await verify_page.goto("https://www.instagram.com/")
    await verify_page.wait_for_timeout(2000)
    
    # Check for login indicators
    is_logged_in = await verify_page.query_selector('svg[aria-label="Home"]')
    if not is_logged_in:
        print("WARNING: Not properly logged in. Cannot proceed.")
        await verify_page.screenshot(path="debug_screenshots/login_verification.png")
        raise Exception("Login verification failed")
    
    print("Login verification successful")
    await verify_page.close()
    
    return context

# ================= STORY DETECTION AND NAVIGATION =================

async def detect_story_type(page: Page) -> str:
    """Detect the type of story being viewed with better accuracy"""
    try:
        # Take a debug screenshot
        await page.screenshot(path=f"debug_screenshots/story_detect_{int(time.time())}.png")
        
        # Check for video elements with broader selectors
        video_elements = await page.query_selector_all('video, svg[aria-label="Video"], div.x78zum5 > div.x1qjc9v5')
        video_error = await page.query_selector('text="Sorry, We\'re having trouble playing this video."')
        
        if video_elements or video_error:
            print("🎬 Detected VIDEO story")
            return "video"
        
        # More robust image detection
        image_elements = await page.query_selector_all([
            'img.xl1xv1r', 
            'img[data-visualcompletion="media-vc-image"]',
            'div.x5yr21d.x1n2onr6.xh8yej3 > img',
            'div.x78zum5 > img'
        ].join(', '))
        
        if image_elements:
            print("🖼️ Detected IMAGE story")
            return "image"
        
        # If we can't specifically identify it but we're in the story viewer
        story_viewer = await page.query_selector('div[role="dialog"]')
        if story_viewer:
            print("📱 Detected story but type unclear - assuming image")
            return "image"  # Default to image for better handling
            
        print("⚠️ Could not detect story type - unknown")
        return "unknown"
    except Exception as e:
        print(f"Error detecting story type: {e}")
        return "unknown"

# async def detect_story_type(page: Page) -> str:
#     """Detect the type of story being viewed (image, video, or unknown)"""
#     try:
#         # Check for video elements
#         video_elements = await page.query_selector_all('video, svg[aria-label="Video"], div.x78zum5 > div.x1qjc9v5')
#         video_error = await page.query_selector('text="Sorry, We\'re having trouble playing this video."')
        
#         if video_elements or video_error:
#             return "video"
        
#         # Check for image elements
#         image_elements = await page.query_selector_all('div.x5yr21d.x1n2onr6.xh8yej3 > img.xl1xv1r, img[data-visualcompletion="media-vc-image"]')
#         if image_elements:
#             return "image"
            
#         # Default to unknown if unable to determine
#         return "unknown"
#     except Exception as e:
#         print(f"Error detecting story type: {e}")
#         return "unknown"

# async def check_end_of_stories(page: Page) -> bool:
#     """Check if we've reached the end of stories"""
#     try:
#         # Look for text indicators of end of stories
#         end_indicators = [
#             "You're all caught up",
#             "No more stories",
#             "All stories viewed"
#         ]
        
#         page_text = await page.evaluate('() => document.body.innerText')
#         for indicator in end_indicators:
#             if indicator in page_text:
#                 return True
                
#         # Check for suggestions grid (appears at end of stories)
#         suggestions = await page.query_selector_all('[data-testid="user-card"], div.x1ja2u2z, div.x6s0dn4.x78zum5.x1q0g3np.x1a02dak')
#         if suggestions and len(suggestions) > 3:
#             return True
            
#         # Check if returned to main feed
#         feed_indicators = await page.query_selector_all('[aria-label="Feed"]')
#         if feed_indicators and len(feed_indicators) > 0:
#             return True
            
#         return False
#     except Exception as e:
#         print(f"Error checking end of stories: {e}")
#         return False


# async def check_end_of_stories(page: Page) -> bool:
#     """Check if we've reached the end of stories with better video story handling"""
#     try:
#         # IMPORTANT: First check if we're on a video story (don't mistakenly identify videos as end)
#         video_indicators = await page.query_selector_all('video, svg[aria-label="Video"], div.x78zum5 > div.x1qjc9v5')
#         video_error = await page.query_selector('text="Sorry, We\'re having trouble playing this video."')
        
#         if video_indicators or video_error:
#             print("⚠️ Currently on a video story - this is NOT the end of stories")
#             return False  # Don't consider a video story as the end
            
#         # Now check for real end indicators
#         end_indicators = [
#             "You're all caught up",
#             "No more stories",
#             "All stories viewed"
#         ]
        
#         page_text = await page.evaluate('() => document.body.innerText')
#         for indicator in end_indicators:
#             if indicator in page_text:
#                 print(f"✅ Found end indicator text: '{indicator}'")
#                 return True
                
#         # More precise checks for end of stories UI elements
#         suggestions = await page.query_selector_all('div[role="button"][tabindex="0"]')
#         if suggestions and len(suggestions) > 5:
#             print(f"✅ Found {len(suggestions)} suggestion elements - likely at end of stories")
#             return True
            
#         # Additional verification for feed view
#         feed = await page.query_selector('svg[aria-label="Feed"], div[role="main"]')
#         if feed:
#             # Double-check we're not in story viewer anymore
#             story_viewer = await page.query_selector('div[role="dialog"] div.x78zum5 img')
#             if not story_viewer:
#                 print("✅ Detected return to main feed - stories ended")
#                 return True
            
#         # If no end indicators are found, we're still in the stories
#         return False
        
#     except Exception as e:
#         print(f"❌ Error checking end of stories: {e}")
#         return False

async def check_end_of_stories(page: Page) -> bool:
    """Check if we've reached the end of stories with better detection logic"""
    try:
        # IMPORTANT: First rule out video stories
        video_indicators = await page.query_selector_all('video, svg[aria-label="Video"], div.x78zum5 > div.x1qjc9v5')
        video_error = await page.query_selector('text="Sorry, We\'re having trouble playing this video."')
        
        if video_indicators or video_error:
            print("⚠️ Currently on a video story - this is NOT the end of stories")
            return False
            
        # Take a debug screenshot to see what we're looking at
        await page.screenshot(path=f"debug_screenshots/end_check_{int(time.time())}.png")
        
        # 1. Check for text indicators of end of stories
        end_indicators = [
            "You're all caught up",
            "No more stories", 
            "All stories viewed",
            "See all stories"
        ]
        
        page_text = await page.evaluate('() => document.body.innerText')
        for indicator in end_indicators:
            if indicator in page_text:
                print(f"✅ Found end indicator text: '{indicator}'")
                return True
                
        # 2. Check for profile suggestion grid (more specific selector)
        suggestion_grid = await page.query_selector('div.x6s0dn4.x78zum5.x1q0g3np.x1a02dak > div > div.x1qjc9v5')
        if suggestion_grid:
            print("✅ Found suggestion grid - stories ended")
            return True
        
        # 3. More reliable check - look for real story content vs end screen
        story_content = await page.query_selector('div.x6s0dn4.x78zum5.xdt5ytf.xl56j7k > img.xl1xv1r, div.x78zum5 > img[data-visualcompletion="media-vc-image"]')
        profile_photos = await page.query_selector_all('img._aa8j')
        
        # FIX: JavaScript syntax -> Python syntax
        if not story_content and len(profile_photos) > 2:
            print("Found multiple profile photos but no story content - likely at end")
            return True
            
        # 4. Check if we left the story viewer completely
        current_url = page.url
        # FIX: JavaScript syntax -> Python syntax
        if "/stories/" not in current_url:
            print("✅ URL changed away from stories - stories ended")
            return True
            
        # If we're still in the story viewer and see story content, we're not at the end
        return False
        
    except Exception as e:
        print(f"❌ Error checking end of stories: {e}")
        return False


async def navigate_to_next_story(page: Page, story_type: str) -> Dict[str, Any]:
    """Navigate to the next story with improved video handling"""
    try:
        print(f"⏭️ Navigating from story type: {story_type}")
        
        # Take before-navigation screenshot for comparison
        before_path = f"debug_screenshots/before_nav_{int(time.time())}.png"
        await page.screenshot(path=before_path)
        
        # For videos, use multiple navigation methods
        if story_type == "video":
            print("🎬 SPECIALIZED VIDEO NAVIGATION")
            
            # Method 1: Try Playwright direct click with force option
            # Try finding the exact button by its specific class combination
            specific_classes = 'div.x1i10hfl.x972fbf.xcfux6l:has(svg[aria-label="Next"])'
            try:
                specific_button = await page.query_selector(specific_classes)
                if specific_button:
                    print("📌 Found button by specific classes - clicking...")
                    await specific_button.click(force=True)
                    await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Class-based click failed: {e}")
            
            # Method 2: Try the exact parent element XPath 
            parent_xpath = '/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/section/div[1]/div/div/div[2]/div[2]/div'
            print(f"🔍 Trying XPath: {parent_xpath}")
            
            await page.evaluate(f'''
                () => {{
                    try {{
                        const nextButtonParent = document.evaluate(
                            "{parent_xpath}", document, null, 
                            XPathResult.FIRST_ORDERED_NODE_TYPE, null
                        ).singleNodeValue;
                        
                        if (nextButtonParent) {{
                            console.log("Found XPath element");
                            
                            // Try clicking at different levels
                            [nextButtonParent, 
                             nextButtonParent.parentElement, 
                             nextButtonParent.parentElement?.parentElement].forEach(el => {{
                                if (el) {{
                                    try {{ 
                                        console.log("Clicking at level:", el.tagName);
                                        el.click();
                                        
                                        // Dispatch synthetic events
                                        const rect = el.getBoundingClientRect();
                                        const centerX = rect.left + rect.width/2;
                                        const centerY = rect.top + rect.height/2;
                                        
                                        [
                                            new MouseEvent('mousedown', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}}),
                                            new MouseEvent('mouseup', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}}),
                                            new MouseEvent('click', {{bubbles: true, cancelable: true, view: window, clientX: centerX, clientY: centerY}})
                                        ].forEach(event => el.dispatchEvent(event));
                                    }} catch(e) {{}}
                                }}
                            }});
                        }}
                    }} catch(e) {{
                        console.error("XPath navigation error:", e);
                    }}
                }}
            ''')
            
            await page.wait_for_timeout(1500)
            
            # Method 3: Keyboard navigation (most reliable in many cases)
            print("🔍 Trying keyboard arrow right...")
            await page.keyboard.press('ArrowRight')
            await page.wait_for_timeout(1500)
            
            # Method 4: Edge click (good for stories in general)
            print("🔍 Trying edge screen click...")
            viewport = await page.evaluate('() => { return {width: window.innerWidth, height: window.innerHeight} }')
            for y_position in [0.3, 0.5, 0.7]:  # Try multiple vertical positions
                await page.mouse.click(viewport['width'] * 0.95, viewport['height'] * y_position)
                await page.wait_for_timeout(500)
        else:
            # For non-video stories, use standard navigation
            next_button = await page.query_selector('div.x6s0dn4.x78zum5.xdt5ytf.xl56j7k, svg[aria-label="Next"]')
            if next_button:
                await next_button.click()
                await page.wait_for_timeout(1000)
            
            await page.keyboard.press('ArrowRight')
            await page.wait_for_timeout(1000)
        
        # Take after-navigation screenshot to verify movement
        after_path = f"debug_screenshots/after_nav_{int(time.time())}.png"
        await page.screenshot(path=after_path)
        
        # Do NOT check for end of stories immediately after video navigation
        # Instead, return success and let the main loop handle detection
        if story_type == "video":
            return {'success': True, 'end_reached': False}
            
        # For non-video stories, check if we've reached the end
        is_end = await check_end_of_stories(page)
        if is_end:
            # time.sleep(10000)
            print("🏁 STOPPING FOR INSPECTION")
            print("Detected end of stories - pausing for 15 seconds to allow inspection")
            await page.wait_for_timeout(15000)  # 15 seconds
            print("🏁 Reached end of stories during navigation")
            return {'success': True, 'end_reached': True}
            
        return {'success': True, 'end_reached': False}
        
    except Exception as e:
        print(f"❌ Navigation error: {e}")
        return {'success': False, 'error': str(e)}

# ================= STORY SCRAPING =================
async def scrape_stories(context: BrowserContext, username: str, start_from: int = 1) -> Dict[str, Any]:
    """Scrape Instagram stories for a given username"""
    print(f"Starting story scraping for {username}")
    
    # Initialize variables
    page = await context.new_page()
    stories_data = []
    story_count = start_from - 1  # Start from the specified story
    max_stories = 50  # Maximum stories to scrape
    consecutive_navigation_failures = 0
    video_story_detection_count = 0
    last_video_story_id = None
    processed_story_ids = set()
    
    try:
        # Navigate to user's stories
        print(f"Navigating to stories for {username}")
        await page.goto(f"https://www.instagram.com/stories/{username}/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # Check if we need to click "View story" button
        view_story_selectors = [
            'div[role="button"]:has-text("View")',
            'div[role="button"]:has-text("view")', 
            'div[role="button"]:has-text("Story")', 
            'div[role="button"]:has-text("story")',
            'div._acan._acap._acas'
        ]
        
        for selector in view_story_selectors:
            try:
                view_button = await page.query_selector(selector)
                if view_button:
                    print(f"Found story prompt with selector: {selector}")
                    print("Clicking 'View story' button for " + username + "...")
                    await view_button.click()
                    await page.wait_for_timeout(3000)
                    break
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue
        
        # Check if story viewer loaded properly
        story_indicator = await page.query_selector('div.x5yr21d.x1n2onr6.xh8yej3 img.xl1xv1r')
        if not story_indicator:
            print("Story viewer did not load properly or user has no stories")
            return {
                "status": "NO_STORIES",
                "data": [],
                "message": "No stories available"
            }
        else:
            print("Proceeding with story extraction for " + username)
        
        # Main story extraction loop
        while story_count < max_stories and consecutive_navigation_failures < 3:
            story_count += 1
            print(f"Processing story {story_count} for {username}")
            
            # Generate a unique ID for this story
            story_id = f"{username}_story_{story_count}"
            
            # Skip if we've already processed this story
            if story_id in processed_story_ids:
                print(f"Skipping already processed story ID: {story_id}")
                continue
                
            processed_story_ids.add(story_id)
            
            # Take a screenshot of the current story
            story_screenshot_path = f"story_screenshots/{username}_{story_count}.png"
            await page.screenshot(path=story_screenshot_path)
            
            # Create story data structure
            story_data = {
                'story_id': story_id,
                'username': username,
                'scraped_at': datetime.datetime.now().isoformat(),
                'screenshot_path': story_screenshot_path
            }
            
            # Detect story type
            story_type = await detect_story_type(page)
            story_data['media_type'] = story_type
            
            # Handle story based on its type
            if story_type == "video":
                print(f"🎬 Detected video story {story_count} - Saving screenshot")
                
                # Special debug screenshot showing the video state
                debug_screenshot_path = f"debug_screenshots/{username}_video_{story_count}.png"
                await page.screenshot(path=debug_screenshot_path)
                story_data['debug_screenshot'] = debug_screenshot_path
                
                # For videos, just save screenshot data without trying to extract media
                story_data['is_video'] = True
                
                # Save this story data immediately 
                collection.update_one({'story_id': story_id}, {'$set': story_data}, upsert=True)
                stories_data.append(story_data)
                
                # Check if we're stuck on the same video
                if story_id == last_video_story_id:
                    video_story_detection_count += 1
                    print(f"⚠️ Same video detected {video_story_detection_count} times")
                    
                    # If we're truly stuck, return what we have so far
                    if video_story_detection_count >= 3:
                        print("🛑 Stuck on same video - ending gracefully")
                        return {
                            "status": "VIDEO_STORY_BLOCKER",
                            "data": stories_data,
                            "last_processed_story": story_count
                        }
                else:
                    # Reset detection counter for new videos
                    video_story_detection_count = 0
                    last_video_story_id = story_id
                
                # IMPORTANT: Use more aggressive navigation for videos
                print("🔄 Using enhanced video story navigation...")
                navigation_result = await navigate_to_next_story(page, "video")
                
                # After video navigation, wait a bit longer and verify we moved
                await page.wait_for_timeout(2000)
                
                # Take another screenshot to verify movement
                await page.screenshot(path=f"debug_screenshots/{username}_after_video_{story_count}.png")
                
                # Continue to next story without further processing this one
                continue

            elif story_type == "image":
                # Try to extract the image URL
                image_element = await page.query_selector('div.x5yr21d.x1n2onr6.xh8yej3 > img.xl1xv1r, img[data-visualcompletion="media-vc-image"]')
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
                
            else:
                # Unknown type, just save screenshot and move on
                story_data['media_type'] = 'unknown'
                collection.update_one({'story_id': story_id}, {'$set': story_data}, upsert=True)
                stories_data.append(story_data)
            
            # Navigate to next story
            navigation_result = await navigate_to_next_story(page, story_type)
            
            # Handle navigation result
            if navigation_result.get('end_reached', False):
                print("🏁 End of stories reached - ending extraction")
                break
                
            # Track navigation failures
            if not navigation_result.get('success', False):
                consecutive_navigation_failures += 1
                print(f"⚠️ Navigation failure {consecutive_navigation_failures}/3")
                
                if consecutive_navigation_failures >= 3:
                    print("Too many navigation failures, ending extraction")
                    break
            else:
                consecutive_navigation_failures = 0
        
        # Return the collected data with status
        return {
            "status": "SUCCESS",
            "data": stories_data,
            "last_processed_story": story_count,
            "total_stories": len(stories_data)
        }
        
    except Exception as e:
        print(f"Error scraping stories for {username}: {str(e)}")
        return {
            "status": "ERROR", 
            "error": str(e),
            "data": stories_data
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
                    if close_button:
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

# ================= MAIN EXECUTION =================
async def main():
    """Main execution function"""
    # Instagram credentials
    username = "insta.25.scra"
    password = "hello@WORLD@2025"
    
    # Target usernames to scrape - replace with your targets
    target_usernames = [
        "arianagrande",
        "kimkardashian",
        "cristiano",
        "kyliejenner",
        "selenagomez",
        "therock"
    ]
    
    # Initialize the browser
    async with async_playwright() as p:
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
        
        # Login to Instagram
        logged_in_context = await login_to_instagram(username, password, browser)
        
        # Randomly select a target username
        random.shuffle(target_usernames)
        random_username = target_usernames[0]
        random_username = "arianagrande"
        
        # Scraping with retry mechanism
        max_retry_attempts = 3
        retry_count = 0
        last_story_num = 0
        all_stories_data = []
        
        print(f"\n{'='*50}\nStarting story scraping for: {random_username}\n{'='*50}\n")
        
        while retry_count < max_retry_attempts:
            try:
                # Start from the story after the last one we processed
                start_from = last_story_num + 1
                
                # Call scrape_stories with the logged in context
                result = await scrape_stories(logged_in_context, random_username, start_from=start_from)
                
                # Check the status code from the result
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
                    if len(all_stories_data) >= 5:
                        print("Already collected a reasonable number of stories, ending gracefully")
                        break
                    
                    print(f"Will retry from story #{start_from + 1}")
                    
                elif status == "NO_STORIES":
                    print("Target has no active stories")
                    break  # No need to retry
                    
                else:  # Any other status like ERROR or UNKNOWN
                    print(f"Received status: {status}, not retrying")
                    if stories:
                        print(f"Still collected {len(stories)} stories")
                    break  # Don't retry for general errors
            
            except Exception as e:
                print(f"Unexpected error during story scraping: {e}")
                break  # Don't retry for unexpected errors
        
        print(f"\n{'='*50}\nCompleted story scraping for: {random_username} with {len(all_stories_data)} total stories\n{'='*50}\n")
        
        # Close the browser
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())