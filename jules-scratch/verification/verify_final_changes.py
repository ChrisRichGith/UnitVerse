from playwright.sync_api import sync_playwright, expect
import time

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # --- Test Schnellkampf and XP Display ---
            page.goto("http://127.0.0.1:5000/")

            # Start a new game to ensure a clean state
            new_game_button = page.get_by_role("button", name="Neues Spiel")
            if new_game_button.is_visible(timeout=5000):
                new_game_button.click()
            else:
                page.get_by_role("button", name="Spiel starten").click()

            page.wait_for_load_state("networkidle")

            # Try to buy up to 3 units to ensure a win
            for _ in range(3):
                buy_buttons = page.get_by_role("button", name="Kaufen").all()
                clicked_a_button = False
                for button in buy_buttons:
                    if button.is_enabled():
                        button.click()
                        clicked_a_button = True
                        break

                if clicked_a_button:
                    page.wait_for_load_state("networkidle")
                else:
                    break # No more affordable units

            # Use Schnellkampf to get to results
            page.get_by_role("button", name="Schnellkampf").click()

            # Wait for the results area to be visible
            results_area = page.locator("#results-area")
            expect(results_area).to_be_visible(timeout=10000)

            # Check if there are any survivors to take a meaningful screenshot
            survivor_container = page.locator(".survivor-container")

            if survivor_container.locator(".unit-card").count() > 0:
                # Verify that the XP div exists in the survivor card
                expect(survivor_container.locator(".unit-card .xp").first).to_be_visible()
                print("Player won. Survivor XP display is present.")
            else:
                print("Player lost. Cannot verify XP display on survivor cards.")

            page.screenshot(path="jules-scratch/verification/final_verification.png")
            print("Screenshot 'jules-scratch/verification/final_verification.png' created.")

        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")

        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()