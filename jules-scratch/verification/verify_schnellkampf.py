from playwright.sync_api import sync_playwright, expect

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # --- Test Schnellkampf (Quick Combat) ---
            page.goto("http://127.0.0.1:5000/")

            # Start a new game
            start_button_no_save = page.get_by_role("button", name="Spiel starten")
            start_button_save_exists = page.get_by_role("button", name="Neues Spiel")

            if start_button_save_exists.is_visible():
                start_button_save_exists.click()
            else:
                start_button_no_save.click()

            # Click Schnellkampf
            page.get_by_role("button", name="Schnellkampf").click()

            # Verify that the results area is visible and speed controls are not
            expect(page.locator("#results-area")).to_be_visible(timeout=5000)
            expect(page.locator("#speed-controls")).not_to_be_visible()

            page.screenshot(path="jules-scratch/verification/schnellkampf_verification.png")
            print("Screenshot 'jules-scratch/verification/schnellkampf_verification.png' created successfully.")

            # --- Test normal combat ---
            page.goto("http://127.0.0.1:5000/")

            # Start a new game
            if start_button_save_exists.is_visible():
                start_button_save_exists.click()
            else:
                start_button_no_save.click()

            # Click normal combat button
            page.get_by_role("button", name="Kauf beenden & Kampf starten").click()

            # Verify that speed controls are visible and results are not (yet)
            expect(page.locator("#speed-controls")).to_be_visible(timeout=5000)
            expect(page.locator("#results-area")).not_to_be_visible()

            page.screenshot(path="jules-scratch/verification/normal_combat_verification.png")
            print("Screenshot 'jules-scratch/verification/normal_combat_verification.png' created successfully.")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")

        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()