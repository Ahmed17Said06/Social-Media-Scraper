import asyncio
import os
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
import csv

# File to save the session state
STORAGE_FILE = "instagram_session.json"

# Login function
async def login_to_instagram(username: str, password: str, browser) -> BrowserContext:
    """Log in to Instagram or load a saved session."""
    # Load session if available
    if os.path.exists(STORAGE_FILE):
        print("Loading saved session...")
        context = await browser.new_context(storage_state=STORAGE_FILE)
    else:
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to Instagram
        await page.goto("https://www.instagram.com/")
        print("Opened Instagram")

        # Wait for the login page to load
        await page.wait_for_selector("input[name='username']", timeout=10000)

        # Fill in the login form
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        print("Filled login credentials")

        # Click the login button
        await page.click("button[type='submit']")
        print("Clicked login")

        # Wait for navigation or confirmation
        try:
            await page.wait_for_selector("nav", timeout=15000)  # Increase timeout
            print("Login successful")

            # Save the session state
            await context.storage_state(path=STORAGE_FILE)
            print(f"Session saved to {STORAGE_FILE}")
        except Exception as e:
            print("Login failed:", e)
            return None

    return context

async def scrape_profile(context: BrowserContext, profile_link: str):
    """Visit and scrape a profile using the provided link."""
    page = await context.new_page()

    try:
        # Navigate to the profile link
        await page.goto(profile_link)
        print(f"Opened profile: {profile_link}")

        # Wait for the profile page to load
        await page.wait_for_selector("header", timeout=10000)
        print(f"Profile page loaded: {profile_link}")

        await asyncio.sleep(1)

        # Open the first post (to start scraping)
        first_post = await page.query_selector('a[href*="/p/"]')
        if first_post:
            await first_post.click()
            print("Clicked on the first post to open it.")
            await page.wait_for_selector('div._a9zs', timeout=15000)  # Wait for the post content container
        else:
            print("No posts found on the profile.")
            return  # Exit if no posts are available

        posts_data = []
        while True:
            await asyncio.sleep(1)  # Allow dynamic elements to load

            # Extracting post data
            post_caption = await page.query_selector('div._a9zs h1')  # Post caption
            post_datetime = await page.query_selector('time._a9ze')  # Post date/time

            # Extract media content using evaluate_all
            media_images = await page.locator('div._aatk img').evaluate_all(
                "elements => elements.map(el => el.src)"
            )

            # Filter out any invalid URLs (e.g., "blob:")
            image_urls = [url for url in media_images if "blob:" not in url]

            # Get the caption and datetime
            caption = await post_caption.inner_text() if post_caption else None
            datetime = await post_datetime.get_attribute('datetime') if post_datetime else None

            # Store post data without video_urls
            post_data = {
                'caption': caption,
                'datetime': datetime,
                'image_urls': image_urls
            }
            posts_data.append(post_data)
            print(f"Scraped post: {post_data}")

            # Navigate to the next post
            next_button = await page.query_selector('svg[aria-label="Next"]')  # Right arrow
            if next_button:
                await next_button.click()
                print("Moved to the next post.")
                await page.wait_for_selector('div._a9zs', timeout=15000)  # Wait for the next post to load
            else:
                print("No more posts found.")
                break  # Exit loop if no next post is available

    except Exception as e:
        print(f"Error scraping profile {profile_link}: {str(e)}")

    finally:
        # Save data to CSV
        try:
            save_to_csv(posts_data)
        except Exception as e:
            print(f"Error saving data to CSV: {e}")

        # Close the page after scraping
        await page.close()


def save_to_csv(posts_data):
    # Define the fieldnames for the CSV file
    fieldnames = ['caption', 'datetime', 'image_urls']

    # Open the CSV file in append mode (or create a new one if it doesn't exist)
    with open('scraped_posts.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write the header if the file is empty
        if file.tell() == 0:
            writer.writeheader()

        # Write the post data
        for post in posts_data:
            # Handle missing values by replacing None with an empty string
            post = {key: (value if value is not None else '') for key, value in post.items()}
            writer.writerow(post)

    print(f"Saved {len(posts_data)} posts to CSV.")





# Concurrency management function
async def scrape_profiles_concurrently(profile_links: list, context: BrowserContext, max_concurrent_tasks: int = 4):
    """Scrape multiple profiles concurrently with a task limit."""
    semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def scrape_with_limit(link):
        async with semaphore:
            await scrape_profile(context, link)

    # Create tasks for scraping
    tasks = [scrape_with_limit(link) for link in profile_links]
    await asyncio.gather(*tasks)

# Main function
async def main():
    # Instagram credentials
    username = "socialmedi51534"
    password = "thisis_B0T"

    # List of profile links to scrape
    profile_links = [
        "https://www.instagram.com/cristiano/",  # Cristiano Ronaldo
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # Log in or load session
        context = await login_to_instagram(username, password, browser)
        if context:
            # Scrape profiles concurrently
            await scrape_profiles_concurrently(profile_links, context)

            # Close the context
            await context.close()

        # Close the browser
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
