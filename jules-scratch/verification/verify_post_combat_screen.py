from playwright.sync_api import sync_playwright, expect
import requests
import json

def setup_test_state():
    test_data = {
        "barracks": [
            {
                "id": "strong-unit-1",
                "level": 10,
                "xp": 0,
                "attributes": { "str": 30, "dex": 30, "con": 30, "int": 30, "wis": 30, "cha": 30 },
                "nickname": "Der Held"
            }
        ]
    }
    requests.post("http://localhost:5000/test_setup", json=test_data)

def run_verification():
    setup_test_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Start a game, which loads the powerful unit from the save file
        page.goto("http://localhost:5000")
        page.get_by_role("button", name="Nächste Runde").click()

        # Deploy the unit
        unit_card_in_barracks = page.locator('.unit-card[data-unit-id="strong-unit-1"]')
        drop_target = page.locator('.slot[data-slot-id="0,0"]')
        unit_card_in_barracks.drag_to(drop_target)

        # Start quick combat
        page.get_by_role("button", name="Schnellkampf").click()

        # On the results screen, the survivor should be highlighted and clickable
        survivor_slot = page.locator('.unit-slot.survivor-unit-slot.clickable')
        expect(survivor_slot).to_be_visible()

        # The unit inside should be our hero
        expect(survivor_slot.locator('.unit-card[data-unit-id="strong-unit-1"]')).to_be_visible()

        # Click the survivor to send it to the barracks
        survivor_slot.click()

        # Check for the success flash message
        expect(page.locator('.flash-messages .success')).to_contain_text("in die Kaserne verschoben")

        # The unit should no longer be clickable
        expect(page.locator('.unit-slot.survivor-unit-slot.clickable')).not_to_be_visible()

        page.screenshot(path="jules-scratch/verification/post_combat_screen.png")

        browser.close()

if __name__ == "__main__":
    run_verification()