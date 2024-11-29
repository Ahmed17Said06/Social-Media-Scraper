import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
import csv

# Directory to save the scraped files
SAVE_DIR = "temp"
os.makedirs(SAVE_DIR, exist_ok=True)

# File to save the session state
STORAGE_FILE = "instagram_session.json"

# Login function
async def login_to_instagram(username: str, password: str, browser) -> BrowserContext:
    """Log in to Instagram or load a saved session."""
    if os.path.exists(STORAGE_FILE):
        print("Loading saved session...")
        context = await browser.new_context(storage_state=STORAGE_FILE)
    else:
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.instagram.com/")
        print("Opened Instagram")

        await page.wait_for_selector("input[name='username']", timeout=10000)

        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        print("Filled login credentials")

        await page.click("button[type='submit']")
        print("Clicked login")

        try:
            await page.wait_for_selector("nav", timeout=15000)
            print("Login successful")
            await context.storage_state(path=STORAGE_FILE)
            print(f"Session saved to {STORAGE_FILE}")
        except Exception as e:
            print("Login failed:", e)
            return None

    return context

async def scrape_profile(context: BrowserContext, profile_link: str, post_limit: int = 10):
    """Scrape a profile and save its data to a CSV file."""
    page = await context.new_page()
    username = urlparse(profile_link).path.strip('/')  # Extract the username from the URL
    file_name = os.path.join(SAVE_DIR, f"{username}.csv")  # Save to the temp directory
    posts_data = []

    try:
        await page.goto(profile_link)
        print(f"Opened profile: {profile_link}")

        await page.wait_for_selector("header", timeout=100000)
        print(f"Profile page loaded: {profile_link}")

        await asyncio.sleep(1)

        first_post = await page.query_selector('a[href*="/p/"]')
        if first_post:
            await first_post.click()
            print("Clicked on the first post to open it.")
            await page.wait_for_selector('div._a9zs', timeout=15000)
        else:
            print("No posts found on the profile.")
            return

        post_count = 0
        while post_count < post_limit:
            await asyncio.sleep(1)

            post_caption = await page.query_selector('div._a9zs h1')
            post_datetime = await page.query_selector('time._a9ze')

            media_images = await page.locator('div._aatk img').evaluate_all(
                "elements => elements.map(el => el.src)"
            )
            image_urls = [url for url in media_images if "blob:" not in url]

            caption = await post_caption.inner_text() if post_caption else None
            datetime = await post_datetime.get_attribute('datetime') if post_datetime else None

            post_data = {
                'caption': caption,
                'datetime': datetime,
                'image_urls': image_urls
            }
            posts_data.append(post_data)
            print(f"Scraped post: {post_data}")

            post_count += 1

            next_button = await page.query_selector('svg[aria-label="Next"]')
            if next_button and post_count < post_limit:
                await next_button.click()
                print("Moved to the next post.")
                await page.wait_for_selector('div._a9zs', timeout=15000)
            else:
                print("No more posts or post limit reached.")
                break

    except Exception as e:
        print(f"Error scraping profile {profile_link}: {str(e)}")
    finally:
        try:
            save_to_csv(posts_data, file_name)
        except Exception as e:
            print(f"Error saving data to CSV: {e}")
        await page.close()

def save_to_csv(posts_data, file_name):
    fieldnames = ['caption', 'datetime', 'image_urls']

    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for post in posts_data:
            post = {key: (value if value is not None else '') for key, value in post.items()}
            writer.writerow(post)

    print(f"Saved {len(posts_data)} posts to {file_name}.")

async def scrape_profiles_concurrently(profile_links: list, context: BrowserContext, max_concurrent_tasks: int = 4, post_limit: int = 10):
    """Scrape multiple profiles concurrently with a task limit."""
    semaphore = asyncio.Semaphore(max_concurrent_tasks)

    async def scrape_with_limit(link):
        async with semaphore:
            await scrape_profile(context, link, post_limit)

    tasks = [scrape_with_limit(link) for link in profile_links]
    await asyncio.gather(*tasks)

async def main():
    username = "socialmedi51534"
    password = "thisis_B0T"

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
                    "https://www.instagram.com/nationalgeographic/", # National Geographic 
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
        browser = await p.chromium.launch(headless=False)

        context = await login_to_instagram(username, password, browser)
        if context:
            await scrape_profiles_concurrently(profile_links, context, post_limit=10)

            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
