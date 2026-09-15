"""
Milestone 48: Automated Clean Demo Flow Capture & Screenshot Recording Script.

Uses headless Microsoft Edge via Chrome DevTools Protocol (CDP) to walk the full
demo sequence in a clean, distraction-free environment:
- No dev tools, no bookmarks bar, full HD 1280x960 viewport.
- 1-Click Demo Login with seeded account demo_user_wardrobe.
- Captures all 6 sequential demo views:
    1. Wardrobe View (/wardrobe)
    2. Candidate Intake & Try-On (/candidates)
    3. Buy Score 6-Axis Radar (/verdict-test)
    4. What-If Lab Combinatorial Subsets (/what-if)
    5. Opportunity Cost Comparison (/opportunity-cost)
    6. Purchase Decision Dashboard (/dashboard)
"""

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
ARTIFACT_DIR = Path(r"C:\Users\anknk\.gemini\antigravity\brain\e4a68fd5-c9b8-4166-b243-53401a90c575")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "recordings_m48"
PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "edge_cdp_profile_m48"

class DemoCDP:
    def __init__(self, port=9222):
        self.port = port
        self.process = None
        self.ws = None
        self.msg_id = 0
        self.pending = {}

    def start(self):
        os.makedirs(PROFILE_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
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
        print(f"Launching Edge on port {self.port}...")
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

    async def connect(self):
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
        print(f"Connected WebSocket: {ws_url}")
        self.ws = await websockets.connect(ws_url, max_size=50 * 1024 * 1024)

        asyncio.create_task(self._listen())
        await self.send("Page.enable")
        await self.send("Runtime.enable")
        await self.send("DOM.enable")

    async def _listen(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                req_id = data.get("id")
                if req_id is not None and req_id in self.pending:
                    fut = self.pending.pop(req_id)
                    if not fut.done():
                        fut.set_result(data)
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

    async def navigate(self, url, wait_seconds=3.0):
        print(f"Navigating to: {url}")
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(wait_seconds)

    async def capture_screen(self, filename):
        data = await self.send("Page.captureScreenshot", {"format": "png"})
        img_data = data["result"]["data"]
        raw_bytes = base64.b64decode(img_data)

        # Save to local output dir
        local_path = OUTPUT_DIR / filename
        with open(local_path, "wb") as f:
            f.write(raw_bytes)

        # Save to artifacts dir
        art_path = ARTIFACT_DIR / filename
        with open(art_path, "wb") as f:
            f.write(raw_bytes)

        print(f"  [SAVED] {filename} ({len(raw_bytes):,} bytes)")
        return art_path

    def stop(self):
        if self.process:
            self.process.kill()
            self.process = None


async def run_flow():
    cdp = DemoCDP()
    try:
        cdp.start()
        await cdp.connect()

        print("\n========================================================")
        print("STAGE 0: 1-CLICK DEMO AUTHENTICATION")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/login", wait_seconds=2.5)

        # Click demo login button
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('1-Click Demo Login'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(2.5)

        # Ensure demo token is in localStorage
        await cdp.evaluate("""
            (() => {
                localStorage.setItem('verdict_demo_token', 'true');
            })()
        """)
        print("Demo authentication established.")

        # ------------------------------------------------------
        # STAGE 1: Wardrobe View
        # ------------------------------------------------------
        print("\n========================================================")
        print("STAGE 1: WARDROBE VIEW (24 CURATED ITEMS)")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/wardrobe", wait_seconds=3.0)
        h1_wardrobe = await cdp.evaluate("document.querySelector('h1')?.innerText")
        print(f"Wardrobe Page Header: {h1_wardrobe}")
        await cdp.capture_screen("m48_step1_wardrobe.png")

        # ------------------------------------------------------
        # STAGE 2: Candidate Intake & Try-On
        # ------------------------------------------------------
        print("\n========================================================")
        print("STAGE 2: CANDIDATE INTAKE & VIRTUAL TRY-ON SIGNALS")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/candidates", wait_seconds=2.5)
        # Click "Load Sample Evaluated Candidate" to showcase pristine Try-On card
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Load Sample'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(1.5)
        h1_cand = await cdp.evaluate("document.querySelector('h1')?.innerText")
        print(f"Candidate Page Header: {h1_cand}")
        await cdp.capture_screen("m48_step2_candidates.png")

        # ------------------------------------------------------
        # STAGE 3: Buy Score Radar (M40 Buy/Skip Split)
        # ------------------------------------------------------
        print("\n========================================================")
        print("STAGE 3: BUY SCORE 6-AXIS RADAR VISUALIZER")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/verdict-test", wait_seconds=2.5)
        # Click BUY demo first
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('BUY (82.5)'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(1.5)
        await cdp.capture_screen("m48_step3_verdict_buy.png")

        # Click SKIP demo to show duplicate detection
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('SKIP (31.7)'));
                if (btn) btn.click();
            })()
        """)
        await asyncio.sleep(1.5)
        await cdp.capture_screen("m48_step3_verdict_skip.png")

        # ------------------------------------------------------
        # STAGE 4: What-If Combinatorial Lab (16 Subsets)
        # ------------------------------------------------------
        print("\n========================================================")
        print("STAGE 4: WHAT-IF LAB COMBINATORIAL OPTIMIZER")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/what-if", wait_seconds=3.0)
        await cdp.capture_screen("m48_step4_what_if.png")
        # Click "Score & Rank 16 Combinations"
        await cdp.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Score & Rank'));
                if (btn) btn.click();
            })()
        """)
        print("Calculating all 16 combinatorial subsets...")
        await asyncio.sleep(4.0)
        # Scroll down slightly to show top recommendation & ranked combinations
        await cdp.evaluate("window.scrollBy(0, 380)")
        await asyncio.sleep(1.0)
        await cdp.capture_screen("m48_step4_what_if_scored.png")

        # ------------------------------------------------------
        # STAGE 5: Opportunity Cost Comparison
        # ------------------------------------------------------
        print("\n========================================================")
        print("STAGE 5: OPPORTUNITY COST COMPARISON (1 VS 2)")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/opportunity-cost", wait_seconds=3.0)
        await cdp.capture_screen("m48_step5_opportunity_cost.png")

        # ------------------------------------------------------
        # STAGE 6: Purchase Decision Dashboard Summary
        # ------------------------------------------------------
        print("\n========================================================")
        print("STAGE 6: PURCHASE DASHBOARD 5-METRIC SUMMARY")
        print("========================================================")
        await cdp.navigate("http://localhost:3000/dashboard", wait_seconds=2.5)
        await cdp.capture_screen("m48_step6_dashboard.png")

        print("\n========================================================")
        print("[SUCCESS] ALL 6 DEMO VIEWS CAPTURED IN CLEAN HD VIEWPORT!")
        print("========================================================\n")

    finally:
        cdp.stop()


if __name__ == "__main__":
    asyncio.run(run_flow())
