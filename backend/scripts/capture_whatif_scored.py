"""
Quick script to capture the scored What-If lab with ranked subsets table.
"""

import asyncio
import base64
import json
import os
import urllib.request
from pathlib import Path
import websockets

ARTIFACT_DIR = Path(r"C:\Users\anknk\.gemini\antigravity\brain\e4a68fd5-c9b8-4166-b243-53401a90c575")

async def capture_what_if_scored():
    res = urllib.request.urlopen("http://127.0.0.1:9222/json/list")
    tabs = json.loads(res.read().decode())
    page_tabs = [t for t in tabs if t.get("type") == "page"]
    ws_url = page_tabs[0]["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
        msg_id = 0

        async def send(method, params=None):
            nonlocal msg_id
            msg_id += 1
            payload = {"id": msg_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                raw = await ws.recv()
                d = json.loads(raw)
                if d.get("id") == msg_id:
                    return d

        await send("Page.navigate", {"url": "http://localhost:3000/what-if"})
        await asyncio.sleep(2.5)

        # Click the "Score & Rank 16 Combinations" button
        await send("Runtime.evaluate", {
            "expression": """
                (() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Score & Rank'));
                    if (btn) {
                        btn.click();
                        return 'CLICKED';
                    }
                    return 'NOT_FOUND';
                })()
            """,
            "returnByValue": True
        })

        print("Waiting for combinatorial subsets calculation (16 subsets)...")
        await asyncio.sleep(4.0)

        # Scroll down slightly to show the top recommendation and ranked combinations
        await send("Runtime.evaluate", {
            "expression": "window.scrollBy(0, 380)"
        })
        await asyncio.sleep(1.0)

        # Capture screenshot
        shot = await send("Page.captureScreenshot", {"format": "png"})
        img_bytes = base64.b64decode(shot["result"]["data"])
        out_path = ARTIFACT_DIR / "m48_step4_what_if_scored.png"
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        print(f"Captured scored What-If: {out_path} ({len(img_bytes)} bytes)")

if __name__ == "__main__":
    asyncio.run(capture_what_if_scored())
