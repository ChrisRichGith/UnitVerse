from playwright.sync_api import sync_playwright, expect
import requests
import json

def setup_test_state():
    test_data = {
        "barracks": [
            {
                "id": "test-unit-rename",
                "level": 1,
                "xp": 0,
                "attributes": { "str": 12, "dex": 12, "con": 12, "int": 12, "wis": 12, "cha": 12 },
                "nickname": None
            }
        ]
    }
    requests.post("http://localhost:5000/test_setup", json=test_data)

def run_verification():
    setup_test_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to the barracks page directly
        page.goto("http://localhost:5000/barracks")

        # Find the unit card and the rename form
        unit_card = page.locator('.unit-card[data-unit-id="test-unit-rename"]')
        nickname_input = unit_card.get_by_placeholder("Spitzname")
        rename_button = unit_card.get_by_role("button", name="Umbenennen")

        # Enter a new nickname and submit
        new_name = "Krieger 'Spike'"
        nickname_input.fill(new_name)
        rename_button.click()

        # Wait for the page to reload and verify the new name is displayed
        header = page.locator('.unit-card[data-unit-id="test-unit-rename"] .unit-card-header strong')
        expect(header).to_contain_text(new_name)

        # Take a screenshot for visual confirmation
        page.screenshot(path="jules-scratch/verification/rename_feature.png")

        browser.close()

if __name__ == "__main__":
    run_verification()