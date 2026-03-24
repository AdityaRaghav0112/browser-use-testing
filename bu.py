# This file makes the browser-use generate a javascript code which scrapes the website


import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent, Browser, ChatGoogle

async def main():
    load_dotenv()

    browser = Browser(headless=False, keep_alive=True, user_data_dir="./browser_profile",)

    llm = ChatGoogle(
        model="gemini-2.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    # agent = Agent(
    #     task="""
    #     1. Open https://www.mcg.gov.in/
    #     2. Hover over Citizen Services
    #     3. Click Property Tax
    #     4. If not loggen in:
    #         - switch the page to english if needed
    #         - Login using mobile number 7015233142
    #         - Wait for OTP entry and pause until user enters it

    #     After login:

    #     6. Open Search Property
    #     7. Select:
    #         Municipality: Gurugram
    #         Colony: AIPL Joy Gallery
    #         Property Category: Commercial
    #     8. Click Search
    #     9. Click on the first property's view details button and inspect the DOM and page source and extract the hidden mobile number
    #     10.Generate a robust javascript function that:
    #         - can be used inside a chrome extension content script
    #         - uses querySelector/querySelectorAll
    #         - avoids fragile class names if possible
    #         - extracts pid, mobile number, and view link for each property
            
    #     11. The Output must;
    #         - Only contain clean JavaScript code
    #         - Be wrapped in a function like: scrapeProperties()
    #         - Include a console.log of the result
    #         - Do not include any explanations
    #         - Do not include any markdown
    #         - Stop after generating the code
    #     """,
    #     llm=llm,
    #     browser=browser,
    # )

    agent = Agent(
    task="""
    1. Go to https://mail.google.com/mail/u/0/#inbox

    2. If not logged in:
        - Enter email: adityaraghav0112@gmail.com
        - Click Next
        - Wait for user to enter password manually

    3. Once inbox is visible:
        - Inspect the DOM structure of the email list
        - Identify each email row container
        - Identify elements for:
            • sender
            • subject
            • preview/snippet
            • date/time

    4. Generate a robust JavaScript function that:
        - Can be used inside a Chrome extension content script
        - Uses querySelector/querySelectorAll
        - Avoids fragile class names if possible
        - Loops through all visible email rows
        - Extracts sender, subject, snippet, and date
        - Returns an array of objects

    5. The output MUST:
        - Only contain clean JavaScript code
        - Be wrapped in a function like: scrapeEmails()
        - Include a console.log of the result

    6. Do NOT explain anything
    7. Do NOT include markdown
    8. Stop after generating the code
    """,
    llm=llm,
    browser=browser,
)

    await agent.run()
    await browser.stop()

asyncio.run(main())