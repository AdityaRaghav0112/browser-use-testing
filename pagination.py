# This file makes the browser-use generate a javascript code which scrapes the website


import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent, Browser, ChatGoogle

async def main():
# The Function it returned for amazon
    # function navigateToPage(pageNumber) {
    #     const links = Array.from(document.querySelectorAll('a, li, button, span'));
    #     const target = links.find(el => el.textContent.trim() === String(pageNumber));
    #     if (target) { 
    #         target.click(); 
    #     } else { 
    #         console.log('Page element not found'); 
    #     }
    # }
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
#     3. Inspect the DOM and find the pagination elements.
#     4. Generate a javascript function that navigates to the next pages automatically.
#     5. Execute the js you just generated.
#     6. Stop the task and the output MUST:
#         - Only contain clean JavaScript code
#         - Be wrapped in a function like: navigateToPage(pageNumber)
#     """,
#     llm=llm,
#     browser=browser
# )
    
    agent = Agent(
        task="""
        1. Navigate to https://www.mcg.gov.in/
        2. Click "Citizen Services" then "Property Tax" (opens new tab — switch to it).
        3. Click "Search Property".
        4. Select municipality "GURUGRAM", colony "aipl joy gallery", property category "commercial" and click on search button.
        5. Scroll down to see search results. You should see "Total Pages" with a number > 1.
        
        6. NOW inspect the pagination DOM using evaluate(). Run this JS:
           `document.querySelector('#searchResultDiv').innerHTML.substring(document.querySelector('#searchResultDiv').innerHTML.lastIndexOf('Total Pages') - 500)`
           This will show you the HTML around the pagination area. Study the output carefully.
        
        8. Based on what you see, write a `navigateToPage(pageNumber)` function.
           IMPORTANT TIPS for this specific website:
           - The page links might use `datacurrentpage` attribute on anchor tags
           - Or they might be simple `<a>` tags with numeric text like "2", "3", etc.
           - Try selectors like: `a[datacurrentpage]`, or anchors whose text matches the page number
           - The function MUST call `.click()` on the found element
           - Return "Success" after clicking, or "Not Found" if element not found
        
        9. Test your function by running: `navigateToPage(2)` using evaluate().
           Then WAIT 5 seconds. Then check if the page content changed (e.g. different property names visible, or the active page indicator changed).
        
        10. If page 2 did NOT load, inspect the DOM again to understand why, fix the function, and RETRY.
            Keep iterating until it actually works.
        
        11. Once verified working, output ONLY the clean JavaScript function.
            The output MUST be exactly in this format:
            function navigateToPage(pageNumber) { ... }
        """,
        llm=llm,
        browser=browser
    )

    result = await agent.run()
    if hasattr(result, 'final_result'):
        print("AGENT RESULT:")
        print(result.final_result())
    else:
        print("AGENT RESULT:", result)
    await browser.stop()

asyncio.run(main())

# The function it returned for muncipal 
# function navigateToPage(pageNumber) {
#     const pageLink = document.querySelector(`a[datacurrentpage="${pageNumber}"]`);
#     if (pageLink) {
#         pageLink.click();
#         return "Success";
#     } else {
#         return "Not Found";
#     }
# }
