"""Offline demo: the full agent loop with a scripted LLM and a real browser.

No API key and no internet needed. A ScriptedLLM replays a fixed plan (the kind of
THINK/ACTION text Gemini produces), while everything else is the real code path:
action parsing, the Playwright tools, the ReAct loop and the LangGraph workflow.

    python examples/offline_demo.py                      # run both modes, headless
    python examples/offline_demo.py --out docs/img       # also write screenshots, GIF, terminal image
    python examples/offline_demo.py --headed             # watch the browser
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402
from rich.console import Console  # noqa: E402

import main as cli  # noqa: E402
from agent_logic import ReActAgent  # noqa: E402
from langgraph_graph import create_agent_graph  # noqa: E402
from tools import BrowserTools  # noqa: E402

SITE_URL = (ROOT / "examples" / "demo_site" / "index.html").as_uri()
TASK = "Demo Shop'ta 'python' ara, sonuçları doğrula ve ekran görüntüsü al"
VIEWPORT = {"width": 1000, "height": 520}


class ScriptedLLM:
    """Replays a fixed plan, one step per call, like a model that answers one ACTION at a time."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = 0

    def generate(self, prompt: str) -> str:
        step = self.steps[min(self.calls, len(self.steps) - 1)]
        self.calls += 1
        return step


def build_plan(screenshot_path: str):
    return [
        f'THINK: Önce demo mağazayı açmalıyım.\nACTION: NAVIGATE("{SITE_URL}")',
        "THINK: Arama kutusuna sorguyu yazmalıyım.\nACTION: FILL(\"input[name='q']\", \"python\")",
        "THINK: Aramayı Enter ile başlatırım.\nACTION: PRESS_ENTER(\"input[name='q']\")",
        f'THINK: Sonuç sayfasının kanıtını alayım.\nACTION: SCREENSHOT("{screenshot_path}")',
        "THINK: Sonuç özetinde 4 sonuç yazmalı.\nACTION: VERIFY_TEXT(\"#summary\", \"4 results\")",
    ]


class RecordingTools(BrowserTools):
    """BrowserTools that also saves a captioned frame after every browser action."""

    ACTIONS = ("navigate", "fill", "press_enter", "click", "select", "verify_text")

    def __init__(self, page, frames_dir: Path):
        super().__init__(page)
        self.frames_dir = frames_dir
        self.frames = []  # (png_path, caption)
        for name in self.ACTIONS:
            setattr(self, name, self._wrap(getattr(self, name)))

    def _wrap(self, fn):
        def inner(*args, **kwargs):
            result = fn(*args, **kwargs)
            path = self.frames_dir / f"step-{len(self.frames) + 1:02d}.png"
            self.page.screenshot(path=str(path))
            self.frames.append((path, result.get("action", "")))
            return result

        return inner


def make_gif(frames, gif_path: Path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed: skipping GIF (pip install pillow)")
        return
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    images = []
    for i, (png, caption) in enumerate(frames, 1):
        frame = Image.open(png).convert("RGB")
        w, h = frame.size
        canvas = Image.new("RGB", (w, h + 40), (24, 28, 36))
        canvas.paste(frame, (0, 0))
        text = f"{i}/{len(frames)}  {caption}".replace(str(ROOT.as_uri()), "…")
        ImageDraw.Draw(canvas).text((14, h + 10), text[:95], fill=(220, 228, 240), font=font)
        images.append(canvas.resize((w * 4 // 5, (h + 40) * 4 // 5)).quantize(colors=96))
    images[0].save(gif_path, save_all=True, append_images=images[1:], duration=1400, loop=0, optimize=True)


def svg_to_png(browser, svg_path: Path, png_path: Path):
    page = browser.new_page(device_scale_factor=1)
    page.goto(svg_path.resolve().as_uri())
    page.locator("svg").first.screenshot(path=str(png_path))
    page.close()
    # the SVG is centred on a white page: trim to the terminal window itself
    from PIL import Image, ImageChops
    img = Image.open(png_path).convert("RGB")
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255))).getbbox()
    if bbox:
        img.crop(bbox).save(png_path)


def run_mode(mode: str, browser, out: Path | None):
    page = browser.new_page(viewport=VIEWPORT)
    shot = str((out or ROOT / "screenshots").resolve() / "results.png")
    Path(shot).parent.mkdir(parents=True, exist_ok=True)
    tools = RecordingTools(page, out) if out else BrowserTools(page)
    llm = ScriptedLLM(build_plan(shot))
    try:
        if mode == "simple":
            result = ReActAgent(llm, tools, max_iterations=10).run(TASK)
        else:
            result = create_agent_graph(llm, tools, max_iterations=10).run(TASK)
    finally:
        page.close()
    return result, tools


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["simple", "graph", "both"], default="both")
    ap.add_argument("--out", type=Path, help="write screenshots, demo.gif and terminal.png here")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    args = ap.parse_args(argv)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)

    modes = ["simple", "graph"] if args.mode == "both" else [args.mode]
    exit_code = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        try:
            for mode in modes:
                result, tools = run_mode(mode, browser, args.out)
                print(f"\n=== mode={mode}: {result['status']} in {result['iterations']} iterations ===")
                if result["status"] != "PASSED":
                    exit_code = 1
                if args.out and mode == "graph":
                    cli.console = Console(record=True, width=96, force_terminal=True, color_system="truecolor")
                    # keep the machine-specific checkout path out of the published image
                    scrub = lambda t: t.replace(str(ROOT), "~/browser-agent")
                    cli.print_result({
                        **result,
                        "message": scrub(result["message"]),
                        "execution_trace": [scrub(line) for line in result["execution_trace"]],
                    })
                    svg = args.out / "terminal.svg"
                    cli.console.save_svg(str(svg), title="Browser Agent")
                    svg_to_png(browser, svg, args.out / "terminal.png")
                    svg.unlink()
                    make_gif(tools.frames, args.out / "demo.gif")
                    for png, _ in tools.frames:
                        png.unlink()
        finally:
            browser.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
