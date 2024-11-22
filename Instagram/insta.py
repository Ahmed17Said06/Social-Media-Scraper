import asyncio
import os
from playwright.async_api import async_playwright

# File to save the session state
STORAGE_FILE = "instagram_session.json"

async def login_to_instagram(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

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

        # Open a new page with the loaded session
        page = await context.new_page()
        await page.goto("https://www.instagram.com/")
        print("Loaded Instagram with session")

        # Keep the browser open for inspection (optional)
        await asyncio.sleep(10)

        # Close the browser
        await browser.close()


if __name__ == "__main__":
    # Replace with your Instagram credentials
    username = "socialmedi51534"
    password = "thisis_B0T"
    asyncio.run(login_to_instagram(username, password))