# Browser-use navigates to the properties page and stops
# LLM scrapes the mucnipal website automatically
# It only works on page 1.


import asyncio
import os
import json
import re
from urllib.parse import urljoin
from dotenv import load_dotenv

from browser_use import Agent, Browser, ChatGoogle
from browser_use.llm.messages import UserMessage


# -----------------------------
# LLM DOM DISCOVERY
# -----------------------------
async def discover_page_logic(page, llm):

    html = await page.evaluate("""
        () => {
            const clone = document.body.cloneNode(true);
            // styles and noscripts can still be removed to save tokens, but keep scripts briefly
            clone.querySelectorAll("style, noscript").forEach(el => el.remove());
            return clone.outerHTML;
        }
    """)

    html = html[:30000]

    prompt = f"""
You are an expert web scraping engineer.
Analyze the following HTML from a property search results page.
Your task is to provide JavaScript code snippets to extract Property IDs (PIDs) and mobile numbers.

Return ONLY a JSON object with these keys:
- "extract_results": A JavaScript arrow function `() => { ... }` that returns an array of objects. 
  Each object MUST have:
  "pid": string (the Property ID)
  "link": string (the URL to the detail page)
  "mobile": string (OPTIONAL, the 10-digit mobile if found on this page, else null)

- "extract_mobile": A JavaScript arrow function `() => { ... }` to be run on the DETAIL page to extract the 10-digit mobile number. **CRITICAL**: The mobile number might be hidden in the HTML source (e.g. inside a script tag or a hidden input). Please check `document.documentElement.outerHTML` or look for specific hidden fields.
- "click_next": A JavaScript arrow function `() => { ... }` that clicks the pagination 'Next' button.

Rules:
1. Do NOT assume specific class names; observe the HTML provided.
2. Return ONLY valid JSON. No markdown backticks.
3. Handle potential nulls/missing elements gracefully within the JS.

HTML:
{html}
"""

    # Retry mechanism for LLM 503 errors
    for i in range(3):
        try:
            response = await llm.ainvoke([UserMessage(content=prompt)])
            break
        except Exception as e:
            if i == 2: raise e
            print(f"LLM call failed (retry {i+1}): {e}")
            await asyncio.sleep(5)

    content = getattr(response, 'completion', getattr(response, 'content', str(response)))

    print("\nRaw LLM response:")
    print(content)

    content = content.replace("```json", "").replace("```", "").strip()

    start = content.find("{")
    end = content.rfind("}")

    if start != -1 and end != -1:
        content = content[start:end+1]

    try:
        logic = json.loads(content)
    except Exception as e:
        print("\n❌ LLM FAILED TO RETURN VALID JSON")
        print(content)
        # Fallback if needed, but let's try to be strict
        raise e

    print("\nDiscovered page logic:")
    print(json.dumps(logic, indent=2))

    return logic


# -----------------------------
# MAIN SCRIPT
# -----------------------------
async def main():

    load_dotenv()

    browser = Browser(headless=False, keep_alive=True)

    llm = ChatGoogle(
        model="gemini-flash-latest",
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    # -------------------------
    # LLM NAVIGATION PHASE
    # -------------------------
    agent = Agent(
        task="""
        1. Open https://www.mcg.gov.in/
        2. Hover over Citizen Services
        3. Click Property Tax
        4. Login using mobile number 7015233142
        5. Wait for OTP entry

        After login:

        6. Open Search Property
        7. Select:
            Municipality: Gurugram
            Colony: AIPL Joy Gallery
            Property Category: Commercial
        8. Click Search

        wait until the parsing is complete of page 1 by our another model, the go to page 2 and so on.
        """,
        llm=llm,
        browser=browser,
    )

    await agent.run()

    browser_session = agent.browser_session
    page = await browser_session.get_current_page()

    if page is None:
        print("Could not get page")
        return

    # -------------------------
    # DISCOVER PAGE STRUCTURE
    # -------------------------
    logic = await discover_page_logic(page, llm)

    results = []
    processed = set()

    # -------------------------
    # SCRAPING LOOP
    # -------------------------
    while True:
        page = await browser_session.get_current_page()
        await asyncio.sleep(3)  # Wait for page to settle
        
        current_url = await page.get_url()
        print(f"\n[Scraper] URL: {current_url}")

        # Extract results using the LLM's script
        cards_raw = await page.evaluate(logic['extract_results'])
        
        # Simple error check: if it's a string, it might be an error from evaluate or we expect list
        if isinstance(cards_raw, str) and ("error" in cards_raw.lower() or "exception" in cards_raw.lower()):
            print("Potential JS Error:", cards_raw)
            logic = await discover_page_logic(page, llm)
            continue

        try:
            cards_data = json.loads(cards_raw) if isinstance(cards_raw, str) else cards_raw
        except:
            cards_data = []

        if not isinstance(cards_data, list):
            cards_data = []

        print(f"Properties found on page: {len(cards_data)}")

        if len(cards_data) == 0:
            print("No properties found. Re-discovering page structure...")
            logic = await discover_page_logic(page, llm)
            await asyncio.sleep(2)
            continue

        for card in cards_data:
            pid = card.get("pid")
            href = card.get("link")
            mobile = card.get("mobile")

            if not pid or pid in processed:
                continue

            processed.add(pid)
            print(f"Processing PID: {pid}")

            if not mobile and href:
                try:
                    # Resolve relative URL
                    full_href = urljoin(current_url, href)
                    
                    # Navigate to detail page
                    await page.goto(full_href)
                    await asyncio.sleep(4) # Wait for detail page load
                    
                    mobile = await page.evaluate(logic['extract_mobile'])
                    
                    # Fallback regex if LLM script failed to return a string or returned null
                    if not mobile or not isinstance(mobile, str) or not re.match(r"[6-9]\d{9}", str(mobile)):
                        # Try a generic regex on the ENTIRE page source (including hidden scripts)
                        source = await page.evaluate("() => document.documentElement.outerHTML")
                        # Look for 10-digit number starting with 6-9
                        matches = re.findall(r"\b[6-9]\d{9}\b", source)
                        if matches:
                            # Filter out known dummy numbers if any (like the login number)
                            login_num = "7015233142"
                            filtered = [m for m in matches if m != login_num]
                            mobile = filtered[0] if filtered else matches[0]
                        else:
                            mobile = None

                    # Go back to search results
                    await page.go_back()
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"Error fetching mobile for {pid}: {e}")
                    # Try to go back anyway
                    try: await page.go_back()
                    except: pass

            results.append({
                "pid": pid,
                "mobile": mobile
            })

            with open("property_data.json", "w") as f:
                json.dump(results, f, indent=2)

        # -------------------------
        # PAGINATION
        # -------------------------
        page = await browser_session.get_current_page()
        print("Attempting pagination...")

        try:
            await page.evaluate(logic['click_next'])
            has_next = True
        except Exception as e:
            print("Pagination error or end of pages:", e)
            has_next = False

        if not has_next:
            print("No more pages found or pagination failed.")
            break

        print("Waiting for next page results...")
        await asyncio.sleep(5)

        await asyncio.sleep(3)

    # -------------------------
    # SAVE RESULTS
    # -------------------------
    with open("property_data.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Saved", len(results), "properties")

    await browser.stop()


asyncio.run(main())