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
PROFILE_DIR = DATA_DIR / "edge_cdp_profile_m40"
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
        tab = page_tabs[0] if page_tabs else None
        if not tab:
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
        except Exception:
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
        data = await self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
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
        print("STAGE 1: 1-CLICK DEMO LOGIN")
        print("==========================================================")
        await cdp.connect_tab("http://localhost:3000/login")
        await asyncio.sleep(2.0)

        # Click 1-Click Demo Login
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('1-Click Demo Login'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(2.5)

        print("\n==========================================================")
        print("STAGE 2: NAVIGATE TO WHAT-IF LAB (/what-if)")
        print("==========================================================")
        await cdp.navigate("http://localhost:3000/what-if")
        await asyncio.sleep(3.0)

        # Wait for candidates in selector shelf
        cand_count = 0
        for _ in range(25):
            cand_count = (
                await cdp.evaluate("document.querySelectorAll('.border-2.rounded-lg').length")
                or 0
            )
            if cand_count > 0:
                break
            await asyncio.sleep(0.4)

        heading = await cdp.evaluate("document.querySelector('h1')?.innerText")
        print("What-If Heading:", heading)
        print(f"Candidate Items Rendered in Shelf: {cand_count}")

        # Ensure all 4 candidates are selected
        print("Ensuring all 4 candidate items are selected...")
        await cdp.evaluate("""
            (() => {
                const cards = document.querySelectorAll('.border-2.rounded-lg');
                cards.forEach(card => {
                    const isSelected = card.className.includes('border-primary') || card.className.includes('bg-primary');
                    if (!isSelected) {
                        card.click();
                    }
                });
            })()
        """)
        await asyncio.sleep(1.0)

        selected_count_badge = await cdp.evaluate("""
            (() => {
                const b = Array.from(document.querySelectorAll('span, div')).find(e => e.innerText && e.innerText.includes('Selected'));
                return b ? b.innerText : null;
            })()
        """)
        print("Selected Shelf Badge:", selected_count_badge)

        print("\n==========================================================")
        print("STAGE 3: TRIGGER WHAT-IF COMBINATORIAL SCORING")
        print("==========================================================")
        score_btn_text = await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Score & Rank'));
                return btn ? btn.innerText.replace(/\\n+/g, ' ') : null;
            })()
        """)
        print("Scoring Button Text:", score_btn_text)

        print("Clicking 'Score & Rank' button...")
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Score & Rank'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(4.0)

        # Verify Hero Recommendation Card
        hero_title = await cdp.evaluate("""
            (() => {
                const h = document.querySelector('.bg-emerald-500\\\\/10, [class*=\"emerald\"]')?.innerText;
                return h || document.querySelector('h2, h3')?.innerText;
            })()
        """)
        print("Hero Recommendation Status:", hero_title[:100] if hero_title else "None")

        # Read the top ranked subset from the UI
        top_subset = await cdp.evaluate("""
            (() => {
                const card = document.querySelector('.border-emerald-500\\\\/40') || document.querySelector('.bg-card');
                return card ? card.innerText.split('\\n').slice(0, 8).join(' | ') : null;
            })()
        """)
        print("Top Subset Details:", top_subset)

        # Verify all combinations rendered
        combinations_count = await cdp.evaluate("""
            (() => {
                const rows = document.querySelectorAll('.space-y-3 > div');
                return rows.length;
            })()
        """)
        print(f"Total Combinations Rendered in List: {combinations_count}")

        # Set tall viewport to capture entire What-If Lab report
        await cdp.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 1280,
                "height": 3200,
                "deviceScaleFactor": 1,
                "mobile": False,
            },
        )
        await asyncio.sleep(1.5)

        # Capture Screenshot
        screenshot_path = os.path.join(ARTIFACT_DIR, "what_if_lab_curated_demo.png")
        await cdp.screenshot(screenshot_path)

        print("\n==========================================================")
        print("CONSOLE AUDIT REPORT")
        print("==========================================================")
        error_logs = [l for l in cdp.console_logs if "error" in l.lower() or "exception" in l.lower()]
        print(f"Total Console Messages: {len(cdp.console_logs)}")
        print(f"Console Errors: {len(error_logs)}")
        for err in error_logs:
            print("  [ERROR]", err)

        if not error_logs:
            print("Zero console errors detected!")

    finally:
        cdp.stop()
        print("\nWhat-If Lab automated demo walkthrough finished cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
