# This page contains similar structure as main2.py but it has a fallback logic 
# The fallback logic contains the class names and ids of the website which is not ideal


import asyncio
import os
import json
from dotenv import load_dotenv

from browser_use import Agent, Browser, ChatGoogle
from browser_use.llm.messages import UserMessage



async def discover_page_logic(page, llm):
    html = await page.evaluate("() => document.body.innerHTML")

    # Try to find the grid/table part specifically to save context
    grid_html = html
    grid_start = html.find("grid")
    if grid_start != -1:
        grid_html = html[max(0, grid_start - 500):]

    prompt = f"""You are analyzing the HTML of a property detail/search page from the MCG (ULB Haryana) website.

Find how to:
1. iterate property cards/rows (usually 'tr' in a '.k-grid-content' OR cards with class '.card')
2. extract property ID (PID) from a single card row (usually the 2nd td OR an element with class '.propertyname')
3. get the "View Details" link for that row
4. extract the mobile number! 
   Note: On the detail page, look for a 10-digit number. It might be in an element with an ID like 'MobileNo', 'txtMobile', or a table cell next to a 'Mobile' label.
5. click the "Next" page button

Return ONLY a JSON object:
{{
 "iterate": "A FULL JavaScript expression that returns an array of elements (e.g. document.querySelectorAll('.card'))",
 "pid": "js expression using 'card' variable (e.g. card.cells[1].innerText.trim())",
 "view_link": "js expression using 'card' variable (e.g. card.querySelector('a').href)",
 "mobile": "A FULL JavaScript expression/IIFE to find the 10-digit mobile number on the detail page. (e.g. (() => {{ ... }})() )",
 "next": "A FULL JavaScript expression to click the next page button"
}}

HTML Snippet:
{grid_html[:20000]}
"""

    response = await llm.ainvoke([UserMessage(content=prompt)])
    content = response.completion
    print("\nRaw LLM response:")
    print(content)

    # Clean JSON
    content = content.replace("```json", "").replace("```", "").strip()
    
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1:
        content = content[start:end+1]

    try:
        logic = json.loads(content)
        
        # Post-process to ensure full JS expressions
        for key in ["iterate", "next"]:
            val = logic[key].strip()
            if val.startswith((".", "#", "[")) or (" " in val and "(" not in val):
                # Looks like a selector, not an expression
                logic[key] = f"document.querySelectorAll('{val}')"
        
    except:
        # Fallback if LLM failed
        print("LLM failed to return JSON or logic invalid, using hardcoded fallbacks")
        logic = {
            "iterate": "document.querySelectorAll('.card.cardheight, .k-grid-content tr')",
            "pid": "(() => { const el = card.querySelector('.propertyname') || card.cells[1]; return el ? el.innerText.split(':').pop().trim() : 'UNKNOWN'; })()",
            "view_link": "card.querySelector('a.btn-primary, a')?.href",
            "mobile": "(() => { const target = document.getElementById('MobileNo') || document.getElementById('txtMobile') || [...document.querySelectorAll('td, span, label')].find(el => /Mobile|मोबाइल/.test(el.innerText)); return (target ? target.innerText : document.body.innerText).match(/\\d{10}/)?.[0] || 'NOT_FOUND'; })()",
            "next": "document.querySelector('.k-pager-next, a[rel=\"next\"]')?.click()"
        }

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

        Stop when property result cards appear.
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

    iterate_expr = logic["iterate"]
    pid_expr = logic["pid"]
    link_expr = logic["view_link"]
    mobile_expr = logic["mobile"]
    next_expr = logic["next"]

    results = []
    processed = set()

    search_url = await page.get_url()

    # -------------------------
    # SCRAPING LOOP
    # -------------------------
    while True:

        await asyncio.sleep(5) # Give it some time

        page = await browser_session.get_current_page()
        url = await page.get_url()
        html = await page.evaluate("() => document.body.innerHTML")
        print(f"\n[Scraper] URL: {url} | HTML Length: {len(html)}")

        cards_data = await page.evaluate(f"""() => {{
            try {{
                const cards = Array.from({iterate_expr});
                console.log('Cards found in JS:', cards.length);
                const data = [];

                cards.forEach(card => {{
                    try {{
                        const pid = {pid_expr};
                        const href = {link_expr};

                        if (pid && href) {{
                            data.push({{pid, href}});
                        }}
                    }} catch(e) {{}}
                }});

                return JSON.stringify(data);
            }} catch(e) {{
                return JSON.stringify({{error: e.message}});
            }}
        }}""")

        cards_json = json.loads(cards_data)
        if isinstance(cards_json, dict) and "error" in cards_json:
            print("JS Error:", cards_json["error"])
            cards_data = []
        else:
            cards_data = cards_json

        print("Cards processed:", len(cards_data))

        # fallback if layout broke
        if len(cards_data) == 0:
            print("Layout changed, rediscovering with LLM...")
            logic = await discover_page_logic(page, llm)

            iterate_expr = logic["iterate"]
            pid_expr = logic["pid"]
            link_expr = logic["view_link"]
            mobile_expr = logic["mobile"]
            next_expr = logic["next"]

            continue

        for card in cards_data:

            pid = card["pid"]
            href = card["href"]

            if not pid or pid in processed:
                continue

            processed.add(pid)

            try:

                page = await browser_session.get_current_page()
                await page.goto(href)

                await asyncio.sleep(3)

                mobile = await page.evaluate(f"""() => {{
                    try {{
                        let m = {mobile_expr};
                        if (!m) {{
                            const text = document.body.innerText;
                            const match = text.match(/\\d{{10}}/);
                            return match ? match[0] : null;
                        }}
                        return m;
                    }} catch(e) {{
                        const text = document.body.innerText;
                        const match = text.match(/\\d{{10}}/);
                        return match ? match[0] : null;
                    }}
                }}""")

                print(pid, mobile)

                results.append({
                    "pid": pid,
                    "mobile": mobile
                })

                # Incremental Save
                with open("property2.json", "w") as f:
                    json.dump(results, f, indent=2)

                page = await browser_session.get_current_page()
                await page.goto(search_url)

                await asyncio.sleep(2)

            except Exception as e:
                print("Error:", pid, e)

        # -------------------------
        # PAGINATION
        # -------------------------
        page = await browser_session.get_current_page()

        has_next = await page.evaluate(f"""() => {{
            try {{
                {next_expr}
                return true;
            }} catch(e) {{
                return false;
            }}
        }}""")

        if not has_next:
            print("No more pages")
            break

        await asyncio.sleep(3)

    # -------------------------
    # SAVE RESULTS
    # -------------------------
    with open("property2.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Saved", len(results), "properties")

    await browser.stop()



asyncio.run(main())