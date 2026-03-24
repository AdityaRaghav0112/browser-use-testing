import asyncio
import os
import json
from dotenv import load_dotenv

from browser_use import Agent, Browser, ChatGoogle



async def main():

    load_dotenv()

    browser = Browser(headless=False, keep_alive=True)

    llm = ChatGoogle(
        model="gemini-flash-latest",
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    # -------------------------
    # LLM PHASE (RUNS ONLY ONCE)
    # -------------------------
    agent = Agent(
        task="""
        1. Open https://www.mcg.gov.in/
        2. Hover over Citizen Services
        3. Click Property Tax
        4. Login using mobile number 7015233142
        5. Wait for OTP entry and pause until user enters it

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
        use_vision=False
    )

    await agent.run()

    # -------------------------
    # CDP SCRAPING PHASE
    # -------------------------

    browser_session = agent.browser_session

    page = await browser_session.get_current_page()

    if page is None:
        print("ERROR: Could not get current page from browser session.")
        await browser.stop()
        return

    results = []
    processed_pids = set()
    search_url = await page.get_url()  # save the search results URL

    while True:

        print("Processing page...")

        # Wait for property cards to load
        await asyncio.sleep(3)

        # Re-get the page to ensure fresh session
        page = await browser_session.get_current_page()
        if page is None:
            print("ERROR: Lost page reference")
            break

        # Extract all PIDs and View Details hrefs from the current page
        page_data = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('.listdatadiv .card');
                const data = [];
                cards.forEach(card => {
                    const nameEl = card.querySelector('.propertyname');
                    const pid = nameEl ? nameEl.innerText.split(':')[1]?.trim() : null;
                    const viewBtn = card.querySelector('a.btn-primary');
                    const href = viewBtn ? viewBtn.href : null;
                    data.push({ pid, href });
                });
                return JSON.stringify(data);
            }
        """)

        import json as json_mod
        cards_data = json_mod.loads(page_data) if page_data else []

        print(f"Found {len(cards_data)} cards on this page")

        for card_info in cards_data:

            pid = card_info.get("pid")
            href = card_info.get("href")

            if not pid or pid in processed_pids:
                continue

            processed_pids.add(pid)

            if not href:
                print(f"No href for PID: {pid}, skipping")
                results.append({"pid": pid, "mobile": None})
                continue

            try:
                # Navigate to the property detail page in the SAME tab
                page = await browser_session.get_current_page()
                if page is None:
                    print("ERROR: Lost page reference")
                    break

                await page.goto(href)
                await asyncio.sleep(3)

                # Re-get page after navigation
                page = await browser_session.get_current_page()
                if page is None:
                    print("ERROR: Lost page after navigation")
                    break

                # Extract mobile number
                mobile = await page.evaluate("""
                    () => {
                        const el = document.querySelector('#MobileNo');
                        return el ? (el.value || el.getAttribute('value') || '') : '';
                    }
                """)

                mobile = mobile.strip() if mobile else None

                print(pid, mobile)

                results.append({
                    "pid": pid,
                    "mobile": mobile
                })

                # Navigate back to the search results page
                await page.goto(search_url)
                await asyncio.sleep(3)

            except Exception as e:
                print("Error processing", pid, e)
                # Try to go back to search results
                try:
                    page = await browser_session.get_current_page()
                    if page:
                        await page.goto(search_url)
                        await asyncio.sleep(3)
                except:
                    print("Could not recover, stopping.")
                    break

        # -------------------------
        # PAGINATION
        # -------------------------

        # Re-get fresh page reference
        page = await browser_session.get_current_page()
        if page is None:
            print("ERROR: Lost page reference for pagination")
            break

        has_next = await page.evaluate("""
            () => {
                const nextIcon = document.querySelector('.fa-step-forward');
                if (!nextIcon) return 'false';
                const link = nextIcon.closest('a');
                if (link) {
                    link.click();
                    return 'true';
                }
                return 'false';
            }
        """)

        if has_next != 'true':
            print("No more pages")
            break

        # Wait for next page to load
        await asyncio.sleep(3)

    # -------------------------
    # SAVE RESULTS
    # -------------------------

    with open("properties.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Saved", len(results), "properties")

    # -------------------------
    # CLEANUP
    # -------------------------
    await browser.stop()


asyncio.run(main())