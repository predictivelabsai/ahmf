"""
Capture Product Demo Video

Playwright script that walks through the entire AHMF platform,
capturing frames for an animated GIF and MP4 video.

Usage:
    python app.py &
    python tests/capture_video.py

Output:
    docs/demo_video.mp4
    docs/demo_video.gif
    docs/frames/*.png
"""

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRAMES_DIR = ROOT / "docs" / "frames"
BASE_URL = "http://localhost:5010"
EMAIL = "joe@ashland-hill.com"
PASSWORD = "test1234"

frame_num = 0


async def capture(page, label, pause=1.0):
    """Capture a frame with a pause for natural pacing."""
    global frame_num
    await asyncio.sleep(pause)
    path = FRAMES_DIR / f"{frame_num:03d}_{label}.png"
    await page.screenshot(path=str(path), type="png")
    print(f"  [{frame_num:03d}] {label}")
    frame_num += 1


async def nav_module(page, path, title, pause=0.8):
    """Navigate to a module via loadModule (updates center pane + right pane copilot)."""
    await page.evaluate(f"""
        () => {{
            if (typeof loadModule === 'function') {{
                loadModule('{path}', '{title}');
            }} else {{
                var c=document.getElementById('center-content');
                var ch=document.getElementById('center-chat');
                if(c&&ch){{ch.style.display='none';c.style.display='block';}}
                htmx.ajax('GET', '{path}', {{target:'#center-content', swap:'innerHTML'}});
                var h=document.getElementById('center-title');
                if(h) h.textContent='{title}';
            }}
        }}
    """)
    await asyncio.sleep(pause)


async def show_chat(page):
    """Switch back to chat view."""
    await page.evaluate("""
        () => {
            if (typeof showChat === 'function') {
                showChat();
            } else {
                var c=document.getElementById('center-content');
                var ch=document.getElementById('center-chat');
                if(c) c.style.display='none';
                if(ch) ch.style.display='block';
                var h=document.getElementById('center-title');
                if(h) h.textContent='AI Chat';
            }
        }
    """)


async def send_chat(page, msg, wait=3.0):
    """Type and send a chat command."""
    await page.evaluate(f"""
        () => {{
            var ta=document.getElementById('chat-input');
            var fm=document.getElementById('chat-form');
            if(ta&&fm){{ ta.value={repr(msg)}; fm.requestSubmit(); }}
        }}
    """)
    await asyncio.sleep(wait)
    # Scroll to bottom
    await page.evaluate("() => { var m=document.getElementById('chat-messages'); if(m) m.scrollTop=m.scrollHeight; }")


async def run():
    from playwright.async_api import async_playwright

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ===== LOGIN =====
        await page.goto(f"{BASE_URL}/login")
        await asyncio.sleep(1)
        await capture(page, "login", 0.5)

        await page.fill('input[name="email"]', EMAIL)
        await page.fill('input[name="password"]', PASSWORD)
        await capture(page, "login_filled", 0.5)

        await page.click('button[type="submit"]')
        await asyncio.sleep(2)

        # ===== WELCOME (new chat) =====
        await page.goto(f"{BASE_URL}/?new=1")
        await asyncio.sleep(2)
        await capture(page, "welcome_screen", 1.5)
        await capture(page, "welcome_screen_hold", 1.0)  # extra frame for pacing

        # ===== CHAT: help =====
        await send_chat(page, "help", 3)
        await capture(page, "chat_help", 1.0)

        # Scroll to see full table
        await page.evaluate("() => { var m=document.getElementById('chat-messages'); if(m) m.scrollTop=m.scrollHeight; }")
        await capture(page, "chat_help_scroll", 0.5)

        # ===== CHAT: portfolio =====
        await send_chat(page, "portfolio", 3)
        await capture(page, "chat_portfolio", 1.0)

        # ===== CHAT: deal:list =====
        await send_chat(page, "deal:list", 3)
        await capture(page, "chat_deals", 1.0)

        # ===== CHAT: incentives =====
        await send_chat(page, "incentives", 3)
        await capture(page, "chat_incentives", 1.0)

        # ===== CHAT: talent search =====
        await send_chat(page, "talent:search Margot Robbie", 3)
        await capture(page, "chat_talent", 1.0)

        # ===== MODULE: Deals =====
        await nav_module(page, "/module/deals", "Deals")
        await capture(page, "module_deals", 1.5)

        # ===== MODULE: Deal Detail =====
        deal_link = await page.evaluate("""
            () => {
                var links = document.querySelectorAll('[onclick*="deal/"]');
                for (var l of links) {
                    var m = l.getAttribute('onclick').match(/loadModule\\('([^']+)','([^']+)'\\)/);
                    if (m && !m[1].includes('/new')) return {path: m[1], title: m[2]};
                }
                return null;
            }
        """)
        if deal_link:
            await nav_module(page, deal_link["path"], deal_link["title"])
            await capture(page, "module_deal_detail", 1.5)

        # ===== MODULE: Contacts =====
        await nav_module(page, "/module/contacts", "Contacts")
        await capture(page, "module_contacts", 1.0)

        # ===== MODULE: Contact Detail =====
        contact_link = await page.evaluate("""
            () => {
                var links = document.querySelectorAll('[onclick*="contact/"]');
                for (var l of links) {
                    var m = l.getAttribute('onclick').match(/loadModule\\('([^']+)','([^']+)'\\)/);
                    if (m) return {path: m[1], title: m[2]};
                }
                return null;
            }
        """)
        if contact_link:
            await nav_module(page, contact_link["path"], contact_link["title"])
            await capture(page, "module_contact_detail", 1.0)
            # Switch to Analytics tab
            await page.evaluate("""
                () => {
                    var tabs = document.querySelectorAll('.contact-tab');
                    for (var t of tabs) { if (t.textContent.trim() === 'Analytics') t.click(); }
                }
            """)
            await asyncio.sleep(1)
            await capture(page, "module_contact_analytics", 1.0)

        # ===== MODULE: Sales & Collections =====
        await nav_module(page, "/module/sales", "Sales & Collections")
        await capture(page, "module_sales", 1.0)

        # ===== MODULE: Credit Rating =====
        await nav_module(page, "/module/credit", "Credit Rating")
        await capture(page, "module_credit", 1.0)

        # ===== MODULE: Accounting =====
        await nav_module(page, "/module/accounting", "Accounting")
        await capture(page, "module_accounting", 1.0)

        # ===== MODULE: Communications =====
        await nav_module(page, "/module/comms", "Communications")
        await capture(page, "module_comms", 1.0)

        # ===== MODULE: Sales Estimates =====
        await nav_module(page, "/module/estimates", "Sales Estimates")
        await capture(page, "module_estimates", 1.0)

        # ===== MODULE: Risk Scoring =====
        await nav_module(page, "/module/risk", "Risk Scoring")
        await capture(page, "module_risk", 1.0)

        # New Risk Assessment form
        await nav_module(page, "/module/risk/new", "New Risk Assessment")
        await capture(page, "module_risk_form", 1.0)

        # ===== MODULE: Smart Budget =====
        await nav_module(page, "/module/budget", "Smart Budget")
        await capture(page, "module_budget", 1.0)

        # ===== MODULE: Scheduling =====
        await nav_module(page, "/module/schedule", "Scheduling")
        await capture(page, "module_schedule", 1.0)

        # ===== MODULE: Soft Funding =====
        await nav_module(page, "/module/funding", "Soft Funding")
        await capture(page, "module_funding", 1.5)

        # ===== MODULE: Data Room =====
        await nav_module(page, "/module/dataroom", "Data Room")
        await capture(page, "module_dataroom", 1.0)

        # Data Room checklist detail
        deal_id = await page.evaluate("""
            async () => {
                const r = await fetch('/module/dataroom');
                const html = await r.text();
                const m = html.match(/hx-get="\\/module\\/dataroom\\/([^"]+)"/);
                return m ? m[1] : null;
            }
        """)
        if deal_id:
            await nav_module(page, f"/module/dataroom/{deal_id}", "Closing Checklist")
            await capture(page, "module_checklist", 1.0)

        # ===== MODULE: Audience Intel =====
        await nav_module(page, "/module/audience", "Audience Intel")
        await capture(page, "module_audience", 1.0)

        # ===== MODULE: Talent Intel =====
        await nav_module(page, "/module/talent", "Talent Intel")
        await capture(page, "module_talent", 1.0)

        # Talent search
        await page.evaluate("""
            () => {
                var input = document.querySelector('#center-content input[type="text"]');
                if(input) input.value = 'Timothée Chalamet';
                var btns = document.querySelectorAll('#center-content button');
                for(var b of btns) { if(b.textContent.trim()==='Search') { b.click(); break; } }
            }
        """)
        await asyncio.sleep(2)
        await capture(page, "module_talent_search", 1.0)

        # ===== MODULE: User Guide =====
        await nav_module(page, "/module/guide", "User Guide")
        await capture(page, "module_guide", 1.0)

        # ===== BACK TO WELCOME =====
        await page.goto(f"{BASE_URL}/?new=1")
        await asyncio.sleep(2)
        await capture(page, "final_welcome", 1.5)

        await browser.close()

    print(f"\n  Captured {frame_num} frames to docs/frames/")


def build_video():
    """Assemble frames into MP4 video and GIF."""
    from PIL import Image
    import av
    import numpy as np

    frames = sorted(FRAMES_DIR.glob("*.png"))
    if not frames:
        print("No frames found!")
        return

    images = [np.array(Image.open(f)) for f in frames]
    print(f"  Building video from {len(images)} frames...")

    # --- MP4 ---
    mp4_path = ROOT / "docs" / "demo_video.mp4"
    fps = 2
    hold_frames = 3  # each screenshot held for 1.5 seconds

    container = av.open(str(mp4_path), mode="w")
    h, w = images[0].shape[:2]
    # Ensure even dimensions for H.264
    w_enc = w if w % 2 == 0 else w - 1
    h_enc = h if h % 2 == 0 else h - 1
    stream = container.add_stream("libx264", rate=fps)
    stream.width = w_enc
    stream.height = h_enc
    stream.pix_fmt = "yuv420p"

    for img in images:
        img_cropped = img[:h_enc, :w_enc, :3]
        frame = av.VideoFrame.from_ndarray(img_cropped, format="rgb24")
        for _ in range(hold_frames):
            for packet in stream.encode(frame):
                container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)
    container.close()
    total_secs = len(images) * hold_frames / fps
    print(f"  Saved MP4: {mp4_path} ({total_secs:.0f}s)")

    # --- GIF ---
    gif_path = ROOT / "docs" / "demo_video.gif"
    pil_frames = []
    for img in images:
        pil_img = Image.fromarray(img[:, :, :3])
        pil_img = pil_img.resize((w // 2, h // 2), Image.LANCZOS)
        pil_frames.append(pil_img)

    pil_frames[0].save(
        str(gif_path), save_all=True, append_images=pil_frames[1:],
        duration=1500, loop=0, optimize=True,
    )
    print(f"  Saved GIF: {gif_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AHMF Product Demo — Video Capture")
    parser.add_argument("--video-only", action="store_true",
                        help="Skip Playwright capture, build video/GIF from existing frames")
    parser.add_argument("--capture-only", action="store_true",
                        help="Capture frames only, skip video/GIF generation")
    args = parser.parse_args()

    if not args.video_only:
        print(f"\n{'='*60}")
        print(f"  AHMF Product Demo — Capturing frames")
        print(f"{'='*60}\n")
        asyncio.run(run())

    if not args.capture_only:
        print(f"\n{'='*60}")
        print(f"  Building video and GIF...")
        print(f"{'='*60}\n")
        build_video()
        print(f"\n  Done!")
        print(f"  MP4: docs/demo_video.mp4")
        print(f"  GIF: docs/demo_video.gif")
        print(f"  Frames: docs/frames/\n")


if __name__ == "__main__":
    main()
