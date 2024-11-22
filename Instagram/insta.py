import asyncio
import os
from playwright.async_api import async_playwright

# File to save the session state
STORAGE_FILE = "instagram_session.json"

async def login_to_instagram(username, password, browser):
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


async def search_target(context, target):
    page = await context.new_page()

    # Navigate to Instagram
    await page.goto("https://www.instagram.com/")
    print("Loaded Instagram")

    # Wait for the search icon or bar to appear using aria-label
    await page.wait_for_selector('svg[aria-label="Search"]')

    # Focus on the search bar
    search_icon_selector = 'svg[aria-label="Search"]'
    await page.click(search_icon_selector)
    print("Search icon clicked")

    # Type the target's name in the search bar
    search_bar_selector = "input[placeholder='Search']"  # Adjust if necessary
    await page.fill(search_bar_selector, target)
    print(f"Searching for: {target}")

    # Wait for the search results to load
    await asyncio.sleep(3)  # Adjust wait time as needed

    # Click on the first search result
    first_result_xpath = "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[1]/div[2]/div/div/div[2]/div/div/div[2]/div/div/div[2]/div/a[1]/div[1]"
    await page.click(f'xpath={first_result_xpath}')
    print("Clicked the first search result")

    # Wait for the target's profile page to load
    await page.wait_for_selector("header")
    print(f"Opened profile for: {target}")

    # Optional: Keep the browser open for inspection
    await asyncio.sleep(10000000000000000000000000000)




async def main():
    # Instagram credentials
    username = "socialmedi51534"
    password = "thisis_B0T"
    target_name = "Cristiano Ronaldo"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # Log in or load session
        context = await login_to_instagram(username, password, browser)
        if context:
            # Perform the search
            await search_target(context, target_name)

            # Close the context
            await context.close()

        # Close the browser
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


