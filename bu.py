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

#     agent = Agent(
#     task="""
#     1. Go to https://www.amazon.in/
#     2. Search for "phones" and wait for the search results page to fully load.
#     3. Inspect the DOM of the search results page carefully:
#         - Find the exact CSS class or attribute used for each product card container
#         - Find the exact CSS class or attribute used for the product title/name text
#         - Find the exact CSS class or attribute used for the price (whole part, fraction part, and currency symbol)
#         - Do NOT assume class names — inspect what is actually present on the page
#     4. Generate a robust javascript function that:
#         - can be used inside a chrome extension content script
#         - uses querySelector/querySelectorAll
#         - avoids fragile class names if possible
#         - extracts product's names and prices
#     5.The output MUST:
#         - Only contain clean JavaScript code
#         - Be wrapped in a function like: scrapeProducts()
#         - Include a console.log of the result
#     6.Now inject the js you just generated in the console.
#     7.scroll to the bottom and move to page 2 and repeat the process.
#     8.After page 2 stop the task
#     """,
#     llm=llm,
#     browser=browser
# )
    
    agent = Agent(
        task="""
        Go to https://www.mcg.gov.in/
        Hover over "citizen services"
        Click on "property tax"
        If not logged in, login using mobile number 7015233142. Wait for otp entry and pause until user enters it.
        After login, click on "search property" from the menu.
        Select the following:
        -municipality: gurugram
        -colony: aipl joy gallery
        -property category: commercial
        Click "search" and wait until search results are fully loaded.
        Inspect the DOM of the search results page carefully:
        - Find the exact CSS class or attribute used for each property card container
        - Find the exact CSS class or attribute used for the property pid/mobile text
        Generate a robust javascript function that:
        - can be used inside a chrome extension content script
        - extracts all the property's PIDs and mobile numbers.
        - moves to the next page and repeats the extraction until there are no more pages left.
        Stop the task and the output MUST:
        - Only contain clean JavaScript code
        - Include a console.log of the result array
        Inject the js 
        """,
        llm=llm,
        browser=browser
    )

    # agent = Agent(
    #     task="""
    #     1. Open https://www.mcg.gov.in/ 
    #     2. Hover over "citizen services" 
    #     3. Click on "property tax" 
    #     4. If not logged in, login using mobile number 7015233142. Wait for otp entry and pause until user enters it.
    #     5. After login, ensure you are on the dashboard 
    #     6. Open "search property" from the menu.
    #     7. Select the following: -municipality: gurugram -colony: aipl joy gallery -property category: commercial 
    #     8. Click "search" and wait until search results are fully loaded.
    #     9. Inspect the DOM of the search results page carefully:
    #      - Find the exact CSS class or attribute used for each property card container
    #      - Find the exact CSS class or attribute used for the property pid/mobile text 
    #     10. Generate a robust javascript function that:
    #         - can be used inside a chrome extension content script
    #         - uses querySelector/querySelectorAll
    #         - avoids fragile class names if possible
    #         - extracts all the property's PIDs and mobile numbers effectively at once
    #     11. The output MUST:
    #         - Only contain clean JavaScript code
    #         - Be wrapped in a function exactly named: scrapeProperties()
    #         - Include a console.log of the result array
    #     12. Now inject the js you just generated in the console and execute it to see the results.
    #     13. Go to page 2 and repeat execute the same js function in the console.
    #     14. stop the task and give me the js you generated and the extracted PIDs and mobile numbers without any explanation or markdown formatting.
    #     """,
    #     llm=llm,
    #     browser=browser,
    # )

#     agent = Agent(
#     task="""
#     1. Go to https://mail.google.com/mail/u/0/#inbox

#     2. If not logged in:
#         - Enter email: adityaraghav0112@gmail.com
#         - Click Next
#         - Wait for user to enter password manually

#     3. Once inbox is visible:
#         - Inspect the DOM structure of the email list
#         - Identify each email row container
#         - Identify elements for:
#             • sender
#             • subject
#             • preview/snippet
#             • date/time

#     4. Generate a robust JavaScript function that:
#         - Can be used inside a Chrome extension content script
#         - Uses querySelector/querySelectorAll
#         - Avoids fragile class names if possible
#         - Loops through all visible email rows
#         - Extracts sender, subject, snippet, and date
#         - Returns an array of objects

#     5. The output MUST:
#         - Only contain clean JavaScript code
#         - Be wrapped in a function like: scrapeEmails()
#         - Include a console.log of the result

#     6. Do NOT explain anything
#     7. Do NOT include markdown
#     8. Stop after generating the code
#     """,
#     llm=llm,
#     browser=browser,
# )

    await agent.run()
    await browser.stop()

asyncio.run(main())