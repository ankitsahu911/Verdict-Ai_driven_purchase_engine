import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
import base64

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DATA_DIR = r"C:\Users\anknk\Desktop\Verdict-Ai_driven_purchase_engine\backend\data"
PROFILE_DIR = os.path.join(DATA_DIR, "edge_cdp_profile")
ARTIFACT_DIR = r"C:\Users\anknk\.gemini\antigravity\brain\e4a68fd5-c9b8-4166-b243-53401a90c575"

class EdgeCDP:
    def __init__(self, port=9222):
        self.port = port
        self.process = None
        self.ws = None
        self.msg_id = 0
        self.console_logs = []

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
        
        await self.send("Page.enable")
        await self.send("Runtime.enable")
        await self.send("Console.enable")
        await self.send("Log.enable")
        asyncio.create_task(self._listen())
        if url and url != "about:blank":
            await self.navigate(url)

    async def _listen(self):
        try:
            async for msg in self.ws:
                data = json.loads(msg)
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
        await self.ws.send(json.dumps(payload))
        return self.msg_id

    async def evaluate(self, expression):
        self.msg_id += 1
        req_id = self.msg_id
        payload = {
            "id": req_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True
            }
        }
        await self.ws.send(json.dumps(payload))
        while True:
            msg = await self.ws.recv()
            data = json.loads(msg)
            if data.get("id") == req_id:
                res = data.get("result", {})
                if "exceptionDetails" in res:
                    raise RuntimeError(f"JS Exception: {res['exceptionDetails']}")
                return res.get("result", {}).get("value")

    async def navigate(self, url):
        await self.evaluate(f"window.location.href = '{url}'")
        await asyncio.sleep(2.5)

    async def screenshot(self, output_path):
        self.msg_id += 1
        req_id = self.msg_id
        payload = {
            "id": req_id,
            "method": "Page.captureScreenshot",
            "params": {"format": "png"}
        }
        await self.ws.send(json.dumps(payload))
        while True:
            msg = await self.ws.recv()
            data = json.loads(msg)
            if data.get("id") == req_id:
                img_data = data["result"]["data"]
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                print(f"Screenshot saved to: {output_path} ({os.path.getsize(output_path)} bytes)")
                return

    def stop(self):
        if self.process:
            self.process.kill()
            self.process = None

async def main():
    cdp = EdgeCDP()
    try:
        cdp.start()
        print("\n==========================================")
        print("STAGE 1: WHAT-IF LAB WALKTHROUGH (/what-if)")
        print("==========================================")
        await cdp.connect_tab("http://localhost:3000/what-if")
        await asyncio.sleep(3.0)
        
        # Verify page heading
        h1 = await cdp.evaluate("document.querySelector('h1')?.innerText")
        print("What-If Heading:", h1)
        
        # Check candidate items loaded in selector
        items_count = await cdp.evaluate("document.querySelectorAll('.grid > div.cursor-pointer').length")
        print("Candidate items displayed in selector shelf:", items_count)
        
        # Read candidate items info
        candidate_info = await cdp.evaluate("""
            Array.from(document.querySelectorAll('.grid > div.cursor-pointer')).map(el => el.innerText.replace(/\\n+/g, ' | '))
        """)
        print("Loaded Candidates:\n", json.dumps(candidate_info, indent=2))
        
        # Click "Score & Rank 16 Combinations" button
        print("\nTriggering 'Score & Rank 16 Combinations' button...")
        clicked = await cdp.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText.includes('Score & Rank') || b.innerText.includes('Evaluating'));
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            })()
        """)
        print("Button clicked:", clicked)
        
        # Wait for scoring to finish and results to appear
        print("Waiting for combination evaluation...")
        for _ in range(30):
            has_results = await cdp.evaluate("Boolean(document.querySelector('h2'))")
            if has_results:
                break
            await asyncio.sleep(0.5)
            
        # Verify Top Recommendation Hero Card
        top_rec_label = await cdp.evaluate("document.querySelector('h2')?.innerText")
        top_rec_score = await cdp.evaluate("document.querySelector('.text-3xl.font-black, .text-4xl.font-black')?.innerText")
        print("\nTOP RECOMMENDATION HERO CARD:")
        print("  Recommendation:", top_rec_label)
        print("  Score & Cart:", top_rec_score)
        
        # Verify Confidence Badge
        confidence_text = await cdp.evaluate("""
            document.querySelector('[data-confidence], .bg-emerald-500\\\\/15, .bg-amber-500\\\\/15, .bg-rose-500\\\\/15')?.innerText
        """)
        print("  Confidence Badge Text:", confidence_text)
        
        # Check Decision Summary Panel on Top Recommendation
        summary_panel_title = await cdp.evaluate("""
            (() => {
                const titles = Array.from(document.querySelectorAll('h3, h4, div')).map(e => e.innerText);
                return titles.find(t => t.includes('Summary Metrics') || t.includes('5-Metric'));
            })()
        """)
        print("  Summary Panel Title:", summary_panel_title)
        
        # Count all ranked strategy cards rendered
        ranked_cards_count = await cdp.evaluate("""
            document.querySelectorAll('.space-y-2\\\\.5 > div, .space-y-3 > div > div').length
        """)
        print(f"Total combinations rendered in ranked list: {ranked_cards_count}")
        
        # Read the top 5 ranked subsets
        top_5_subsets = await cdp.evaluate("""
            Array.from(document.querySelectorAll('.space-y-2\\\\.5 > div')).slice(0, 5).map(el => {
                const rank = el.querySelector('.font-mono')?.innerText || '';
                const title = el.querySelector('.font-extrabold')?.innerText || '';
                const score = el.querySelector('.font-extrabold.text-sm')?.innerText || '';
                const reason = el.querySelector('.text-xs.text-muted-foreground')?.innerText || '';
                return `${rank}: ${title} -> Score: ${score} (${reason})`;
            })
        """)
        print("\nTop 5 Ranked Subsets:\n", json.dumps(top_5_subsets, indent=2))
        
        # Expand subset #1 to verify 6-axis breakdown and compact summary panel
        print("\nClicking on Rank #1 row to expand details...")
        await cdp.evaluate("""
            const firstRow = document.querySelector('.space-y-2\\\\.5 > div');
            if (firstRow) firstRow.querySelector('.cursor-pointer')?.click();
        """)
        await asyncio.sleep(1.0)
        
        # Set tall viewport to capture full page
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 2400,
            "deviceScaleFactor": 1,
            "mobile": False
        })
        
        # Verify expanded 6-axis breakdown
        axes_rendered = await cdp.evaluate("""
            Array.from(document.querySelectorAll('.grid-cols-2 > div')).map(el => el.innerText.replace(/\\n+/g, ' | '))
        """)
        print("Expanded 6 Axes rendered:", len(axes_rendered))
        
        # Capture What-If Lab Screenshot
        what_if_screenshot = os.path.join(ARTIFACT_DIR, "what_if_lab_organic.png")
        await cdp.screenshot(what_if_screenshot)
        
        print("\n================================================")
        print("STAGE 2: OPPORTUNITY COST WALKTHROUGH (/opportunity-cost)")
        print("================================================")
        await cdp.navigate("http://localhost:3000/opportunity-cost")
        await asyncio.sleep(2.5)
        
        opp_heading = await cdp.evaluate("document.querySelector('h1')?.innerText")
        print("Opportunity Cost Heading:", opp_heading)
        
        # Step 1: Select Candidate #6 (Olive Outerwear $115) as primary
        print("\nSelecting Candidate #6 (Olive Outerwear) as Primary Candidate...")
        await cdp.evaluate("""
            (() => {
                const grids = document.querySelectorAll('.grid');
                if (grids.length >= 1) {
                    const cards = Array.from(grids[0].children);
                    const c6 = cards.find(c => c.innerText.includes('Olive') || c.innerText.includes('115'));
                    if (c6) c6.click();
                }
            })()
        """)
        await asyncio.sleep(0.8)
        
        # Step 2: In alternative bundle grid, ensure Candidate #4 (Beige $48) and #5 (Charcoal $62) are selected
        print("Configuring Alternative Bundle: Candidate #4 ($48) + Candidate #5 ($62)...")
        await cdp.evaluate("""
            (() => {
                const grids = document.querySelectorAll('.grid');
                if (grids.length >= 2) {
                    const cards = Array.from(grids[1].children);
                    const c4 = cards.find(c => c.innerText.includes('Beige') || c.innerText.includes('48'));
                    const c5 = cards.find(c => c.innerText.includes('Charcoal') || c.innerText.includes('62'));
                    const c7 = cards.find(c => c.innerText.includes('White') || c.innerText.includes('70'));
                    
                    // Unselect c7 if selected
                    if (c7 && c7.className.includes('bg-emerald-500/10')) {
                        c7.click();
                    }
                    // Ensure c4 is selected
                    if (c4 && !c4.className.includes('bg-emerald-500/10')) {
                        c4.click();
                    }
                    // Ensure c5 is selected
                    if (c5 && !c5.className.includes('bg-emerald-500/10')) {
                        c5.click();
                    }
                }
            })()
        """)
        await asyncio.sleep(0.8)
        
        # Check alternative selection count
        alt_status = await cdp.evaluate("""
            document.querySelector('.pt-2.border-t .font-bold')?.innerText
        """)
        print("Step 2 Selection Status Badge:", alt_status)
        
        # Click "Compare Opportunity Cost"
        print("Clicking 'Compare Opportunity Cost' button...")
        await cdp.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText.includes('Compare Opportunity Cost') || b.innerText.includes('Computing'));
                if (btn) btn.click();
            })()
        """)
        
        # Wait for comparison card to render
        print("Waiting for comparison results to render...")
        for _ in range(30):
            has_verdict = await cdp.evaluate("Boolean(document.querySelector('h2'))")
            if has_verdict:
                break
            await asyncio.sleep(0.5)
            
        opp_verdict_h2 = await cdp.evaluate("document.querySelector('h2')?.innerText")
        print("\nOPPORTUNITY COST HEADLINE:")
        print(" ", opp_verdict_h2)
        
        # Delta chips
        deltas = await cdp.evaluate("""
            Array.from(document.querySelectorAll('.flex.flex-wrap > div')).map(el => el.innerText.replace(/\\n+/g, ' '))
        """)
        print("Trade-Off Delta Badges:", deltas)
        
        # Check Candidate Card (Left Column)
        cand_card_title = await cdp.evaluate("document.querySelector('.lg\\\\:col-span-5 h3')?.innerText")
        cand_score = await cdp.evaluate("document.querySelector('.lg\\\\:col-span-5 .font-mono.text-base')?.innerText")
        print(f"\nOption A Candidate: {cand_card_title} (Score: {cand_score})")
        
        # Check Alternative Bundle Card (Right Column)
        alt_bundle_title = await cdp.evaluate("document.querySelectorAll('.lg\\\\:col-span-5')[1]?.querySelector('span')?.innerText")
        alt_bundle_score = await cdp.evaluate("document.querySelectorAll('.lg\\\\:col-span-5')[1]?.querySelector('.font-mono.text-base')?.innerText")
        print(f"Option B Alternative: {alt_bundle_title} (Score: {alt_bundle_score})")
        
        # Set tall viewport to capture full Opportunity Cost comparison card
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": 1280,
            "height": 2000,
            "deviceScaleFactor": 1,
            "mobile": False
        })
        await asyncio.sleep(0.5)

        # Capture Opportunity Cost Screenshot
        opp_screenshot = os.path.join(ARTIFACT_DIR, "opportunity_cost_organic.png")
        await cdp.screenshot(opp_screenshot)
        
        print("\n==========================================")
        print("CONSOLE AUDIT & VERIFICATION REPORT")
        print("==========================================")
        error_logs = [l for l in cdp.console_logs if "error" in l.lower() or "exception" in l.lower()]
        print(f"Total Console Messages Captured: {len(cdp.console_logs)}")
        print(f"Console Errors: {len(error_logs)}")
        for err in error_logs:
            print("  [ERROR]", err)
            
        if not error_logs:
            print("Zero console errors detected during entire walkthrough!")
            
    finally:
        cdp.stop()
        print("\nWalkthrough completed cleanly.")

if __name__ == "__main__":
    asyncio.run(main())
