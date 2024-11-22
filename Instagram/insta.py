import asyncio
import os
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright

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
        await page.wait_for_selector("input[name='username']")

        # Fill in the login form
        await page.fill("input[name='username']", username)
        await page.fill("input[name='password']", password)
        print("Filled login credentials")

        # Click the login button
        await page.click("button[type='submit']")
        print("Clicked login")

        # Wait for navigation or confirmation
        try:
            await page.wait_for_selector("nav", timeout=10000)
            print("Login successful")

            # Save the session state
            await context.storage_state(path=STORAGE_FILE)
            print(f"Session saved to {STORAGE_FILE}")
        except Exception as e:
            print("Login failed:", e)
            return None

    return context

# Profile scraping function
async def scrape_profile(context: BrowserContext, profile_link: str):
    """Visit and scrape a profile using the provided link."""
    page = await context.new_page()

    # Navigate to the profile link
    await page.goto(profile_link)
    print(f"Opened profile: {profile_link}")

    # Wait for the profile page to load
    await page.wait_for_selector("header")
    print(f"Profile page loaded: {profile_link}")

    # Optional: Add scraping logic here for bio, posts, etc.
    await asyncio.sleep(5)  # Simulate scraping delay

    # Close the page
    await page.close()

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
        "https://www.instagram.com/leomessi/",   # Lionel Messi
        "https://www.instagram.com/neymarjr/",   # Neymar Jr.
        "https://www.instagram.com/kyliejenner/",  # Kylie Jenner
        "https://www.instagram.com/therock/",   # Dwayne 'The Rock' Johnson
        "https://www.instagram.com/kimkardashian/",  # Kim Kardashian
        "https://www.instagram.com/arianagrande/",  # Ariana Grande
        "https://www.instagram.com/selenagomez/",  # Selena Gomez
        "https://www.instagram.com/beyonce/",  # Beyoncé
        "https://www.instagram.com/justinbieber/",  # Justin Bieber
        "https://www.instagram.com/taylorswift/",  # Taylor Swift
        "https://www.instagram.com/nike/",  # Nike
        "https://www.instagram.com/nationalgeographic/",  # National Geographic
        "https://www.instagram.com/khaby00/",  # Khaby Lame
        "https://www.instagram.com/virat.kohli/",  # Virat Kohli
        "https://www.instagram.com/jlo/",  # Jennifer Lopez
        "https://www.instagram.com/iamcardib/",  # Cardi B
        "https://www.instagram.com/kevinhart4real/",  # Kevin Hart
        "https://www.instagram.com/kingjames/",  # LeBron James
        "https://www.instagram.com/dualipa/",  # Dua Lipa
        "https://www.instagram.com/eminem/",  # Eminem
        "https://www.instagram.com/badgalriri/",  # Rihanna
        "https://www.instagram.com/rogerfederer/",  # Roger Federer
        "https://www.instagram.com/chrishemsworth/",  # Chris Hemsworth
        "https://www.instagram.com/shakira/",  # Shakira
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
