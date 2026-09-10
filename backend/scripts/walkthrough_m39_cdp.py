import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_DIR = DATA_DIR / "edge_cdp_profile_m39"
ARTIFACT_DIR = r"C:\Users\anknk\.gemini\antigravity\brain\e4a68fd5-c9b8-4166-b243-53401a90c575"

class EdgeCDP:
    def __init__(self, port=9222):
        self.port = port
        self.process = None
        self.ws = None
        self.msg_id = 0
        self.console_logs = []
        self.pending = {}

    def start(self):
        os.makedirs(PROFILE_DIR, exist_ok=True)
        cmd = [
            EDGE_PATH,
            "--headless=new",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={PROFILE_DIR}",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,960",
            "http://localhost:3000/login",
        ]
        print(f"Launching Edge with remote debugging on port {self.port}...")
        self.process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        for _ in range(30):
            try:
                res = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=1)
                data = json.loads(res.read().decode())
                print(f"Connected to Edge: {data.get('Browser')}")
                return
            except Exception:
                time.sleep(0.3)
        raise RuntimeError("Failed to connect to Edge remote debugging port.")

    async def connect_tab(self, url="about:blank"):
        import websockets
        res = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list")
        tabs = json.loads(res.read().decode())
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if page_tabs:
            tab = page_tabs[0]
        else:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/new", method="PUT")
            res = urllib.request.urlopen(req)
            tab = json.loads(res.read().decode())
        ws_url = tab["webSocketDebuggerUrl"]
        print(f"Connecting to tab: {tab.get('id')} -> {url}")
        self.ws = await websockets.connect(ws_url, max_size=50 * 1024 * 1024)
        
        asyncio.create_task(self._listen())
        await self.send("Page.enable")
        await self.send("Runtime.enable")
        await self.send("Console.enable")
        await self.send("Log.enable")
        if url and url != "about:blank":
            await self.navigate(url)

    async def _listen(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                req_id = data.get("id")
                if req_id is not None and req_id in self.pending:
                    fut = self.pending.pop(req_id)
                    if not fut.done():
                        fut.set_result(data)
                        
                method = data.get("method")
                if method == "Console.messageAdded":
                    msg_obj = data["params"]["message"]
                    self.console_logs.append(f"[{msg_obj.get('level')}] {msg_obj.get('text')}")
                elif method == "Runtime.consoleAPICalled":
                    args = data["params"].get("args", [])
                    texts = [str(a.get("value", a.get("description", ""))) for a in args]
                    self.console_logs.append(f"[{data['params']['type']}] {' '.join(texts)}")
        except Exception as e:
            pass

    async def send(self, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending[self.msg_id] = fut
        await self.ws.send(json.dumps(payload))
        return await fut

    async def evaluate(self, expression):
        data = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        res = data.get("result", {})
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS Exception: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    async def navigate(self, url):
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(2.5)

    async def screenshot(self, output_path):
        data = await self.send("Page.captureScreenshot", {"format": "png"})
        img_data = data["result"]["data"]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(img_data))
        print(f"Screenshot saved to: {output_path} ({os.path.getsize(output_path)} bytes)")

    def stop(self):
        if self.process:
            self.process.kill()
            self.process = None

async def main():
    cdp = EdgeCDP()
    try:
        cdp.start()
        print("\n==========================================================")
        print("STAGE 1: 1-CLICK DEMO ACCOUNT LOGIN WALKTHROUGH (/login)")
        print("==========================================================")
        await cdp.connect_tab("http://localhost:3000/login")
        await asyncio.sleep(2.0)
        
        login_h1 = await cdp.evaluate("document.querySelector('h1')?.innerText")
        print("Login Page Heading:", login_h1)
        
        # Verify 1-Click Demo Login button exists
        demo_btn_text = await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('1-Click Demo Login'));
                return btn ? btn.innerText.replace(/\\n+/g, ' ') : null;
            })()
        """)
        print("Demo Login Button:", demo_btn_text)
        
        # Click 1-Click Demo Login button
        print("\nClicking 1-Click Demo Login button...")
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('1-Click Demo Login'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(3.0)
        
        print("\n==========================================================")
        print("STAGE 2: CURATED DEMO WARDROBE VERIFICATION (/wardrobe)")
        print("==========================================================")
        current_url = await cdp.evaluate("window.location.href")
        print("Current URL after login:", current_url)
        
        # Verify header title & badge
        # Wait for wardrobe garment cards to load
        garment_cards_count = 0
        for _ in range(30):
            garment_cards_count = await cdp.evaluate("document.querySelectorAll('.grid > div').length") or 0
            if garment_cards_count > 0:
                break
            await asyncio.sleep(0.4)

        wardrobe_heading = await cdp.evaluate("document.querySelector('h2')?.innerText")
        preverified_badge = await cdp.evaluate("""
            (() => {
                const badges = Array.from(document.querySelectorAll('span, div')).filter(e => e.innerText && e.innerText.includes('Pre-Verified'));
                return badges[0]?.innerText || null;
            })()
        """)
        print("Wardrobe Heading:", wardrobe_heading)
        print("Pre-Verified Badge:", preverified_badge)
        print(f"Total Garment Cards Rendered in UI Grid: {garment_cards_count}")
        
        # Read sample garments rendered in UI
        sample_cards = await cdp.evaluate("""
            Array.from(document.querySelectorAll('.grid > div')).slice(0, 5).map(c => {
                const badges = Array.from(c.querySelectorAll('.text-\\\\[11px\\\\]')).map(b => b.innerText);
                const hasImg = Boolean(c.querySelector('img'));
                return {
                    badges: badges.join(' • '),
                    hasImage: hasImg
                };
            })
        """)
        print("Sample Rendered Garment Cards in Wardrobe:\n", json.dumps(sample_cards, indent=2))
        
        print("\n==========================================================")
        print("STAGE 3: M9 MANUAL CORRECTION FEATURE AUDIT")
        print("==========================================================")
        # Find and click edit button on the first garment
        print("Clicking edit button on first garment card...")
        opened_dialog = await cdp.evaluate("""
            (() => {
                const firstCard = document.querySelector('.grid > div');
                if (firstCard) {
                    const editBtn = firstCard.querySelector('button[aria-label=\"Edit attributes\"]');
                    if (editBtn) {
                        editBtn.click();
                        return true;
                    }
                }
                return false;
            })()
        """)
        print("Edit dialog opened:", opened_dialog)
        await asyncio.sleep(1.0)
        
        # Check dialog title
        dialog_title = await cdp.evaluate("document.querySelector('[role=\"dialog\"] h2, [role=\"dialog\"] div')?.innerText")
        print("Edit Dialog Title:", dialog_title)
        
        # Modify an attribute (e.g. style)
        print("Updating attribute 'style' to 'Smart Casual (Verified)'...")
        modified = await cdp.evaluate("""
            (() => {
                const input = document.querySelector('#edit-style');
                if (input) {
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, 'Smart Casual (Verified)');
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            })()
        """)
        print("Attribute modified:", modified)
        await asyncio.sleep(0.5)

        # Click save
        print("Clicking 'Save'...")
        saved = await cdp.evaluate("""
            (() => {
                const dialog = document.querySelector('[role=\"dialog\"]');
                if (!dialog) return false;
                const saveBtn = Array.from(dialog.querySelectorAll('button')).find(b => b.innerText.includes('Save'));
                if (saveBtn) {
                    saveBtn.click();
                    return true;
                }
                return false;
            })()
        """)
        print("Save button clicked:", saved)
        await asyncio.sleep(2.0)
        
        # Set tall viewport to capture full wardrobe grid
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 2600,
            "deviceScaleFactor": 1,
            "mobile": False
        })
        await asyncio.sleep(1.0)
        
        # Capture Screenshot of Verified Demo Wardrobe Grid
        demo_screenshot = os.path.join(ARTIFACT_DIR, "demo_wardrobe_verified.png")
        await cdp.screenshot(demo_screenshot)
        
        print("\n==========================================================")
        print("CONSOLE AUDIT REPORT")
        print("==========================================================")
        error_logs = [l for l in cdp.console_logs if "error" in l.lower() or "exception" in l.lower()]
        print(f"Total Console Messages Captured: {len(cdp.console_logs)}")
        print(f"Console Errors: {len(error_logs)}")
        for err in error_logs:
            print("  [ERROR]", err)
            
        if not error_logs:
            print("Zero console errors detected during entire demo walkthrough!")
            
    finally:
        cdp.stop()
        print("\nDemo walkthrough script finished cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
