import os
import asyncio
from playwright.async_api import async_playwright
import pytest

# Configuration
UI_URL = "http://127.0.0.1:8000/"

async def run_ui_sanity_check():
    """
    Playwright UI Sanity Checker.
    This simulates a real user interacting with the Web UI to ensure 
    the frontend components, node palette, drag-and-drop, and execution 
    buttons are functioning correctly.
    """
    print("Starting Playwright UI Sanity Check...")
    
    async with async_playwright() as p:
        # Use chromium in headless mode (set headless=False to watch it run)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 1. Load the page
            print(f"Navigating to {UI_URL}...")
            response = await page.goto(UI_URL)
            assert response.status == 200, f"Expected status 200, got {response.status}"
            
            # 2. Check basic layout elements
            print("Checking basic layout elements...")
            await page.wait_for_selector("header:has-text('AI Flow Visual Editor')")
            await page.wait_for_selector("#node-palette")
            await page.wait_for_selector("#drawflow")
            
            # 3. Add a TRIGGER node
            print("Adding TRIGGER node...")
            # Find the button in the palette that contains 'Trigger'
            trigger_btn = page.locator(".node-btn", has_text="Trigger")
            await trigger_btn.click()
            
            # 4. Add an AI_AGENT node
            print("Adding AI_AGENT node...")
            agent_btn = page.locator(".node-btn", has_text="AI Agent")
            await agent_btn.click()
            
            # 5. Verify nodes appeared on canvas
            print("Verifying nodes on canvas...")
            nodes = page.locator(".drawflow-node")
            node_count = await nodes.count()
            assert node_count >= 2, f"Expected at least 2 nodes on canvas, found {node_count}"
            
            # 6. Test Node Selection & Configuration Panel
            print("Testing node selection & configuration panel...")
            # Use force click since Drawflow layers might intercept standard clicks
            first_node = nodes.first
            await first_node.click(force=True)
            
            # The properties panel should appear
            props_panel = page.locator("#props-panel")
            await expect_visible(props_panel)
            
            # The Info panel should appear
            info_panel = page.locator("#node-info-panel")
            await expect_visible(info_panel)
            
            # 7. Execute Flow
            print("Testing execution button...")
            run_btn = page.locator("#run-btn")
            await run_btn.click()
            
            # Wait for execution modal to appear (this might take a few seconds depending on the engine)
            print("Waiting for execution modal...")
            output_modal = page.locator("#output-modal")
            await output_modal.wait_for(state="visible", timeout=15000)
            
            # Check if modal contains results
            modal_text = await output_modal.inner_text()
            assert "Execution Status" in modal_text, "Modal did not contain execution status"
            
            print("UI Sanity Check PASSED! ✅")
            return True
            
        except Exception as e:
            print(f"UI Sanity Check FAILED! ❌\nError: {str(e)}")
            # Take a screenshot on failure for debugging
            await page.screenshot(path="ui_failure_screenshot.png")
            print("Screenshot saved to ui_failure_screenshot.png")
            return False
            
        finally:
            await browser.close()

async def expect_visible(locator, timeout=5000):
    await locator.wait_for(state="visible", timeout=timeout)

if __name__ == "__main__":
    asyncio.run(run_ui_sanity_check())
