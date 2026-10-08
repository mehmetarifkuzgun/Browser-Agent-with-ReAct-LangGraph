import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent_logic import GeminiLLM, ReActAgent
from tools import BrowserTools
from langgraph_graph import create_agent_graph


load_dotenv()

console = Console()


def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║           🤖 BROWSER AGENT 🤖                        ║
    ║                                                       ║
    ║        Python + LangGraph + Playwright               ║
    ║        ReAct Pattern Implementation                  ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def validate_env():
    api_key = os.getenv("GEMINI_API_KEY")
    
    placeholders = ("your_gemini_api_key_here", "<YOUR-API-KEY-GOES-HERE>")
    if not api_key or api_key.strip() in placeholders or api_key.startswith("your_"):
        console.print("\n❌ [bold red]HATA: GEMINI_API_KEY bulunamadı![/bold red]", style="bold red")
        console.print("\n📝 Çözüm adımları:", style="bold yellow")
        console.print("1. .env.example dosyasını kopyalayın: [cyan]cp .env.example .env[/cyan]")
        console.print("2. .env dosyasını düzenleyin ve gerçek API key'inizi ekleyin")
        console.print("3. API key almak için: [cyan]https://makersuite.google.com/app/apikey[/cyan]")
        sys.exit(1)
    
    return api_key


def get_user_task() -> str:
    console.print("\n" + "="*60, style="bold blue")
    console.print("📝 [bold green]Görev Girin:[/bold green]")
    console.print("="*60 + "\n", style="bold blue")
    
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        console.print(f"[dim]→ {task}[/dim]\n")
        return task
    
    console.print("[dim]Örnek: 'Amazon Türkiye'de 'python kitap' ara sonucu ekran görüntüsü olarak kaydet'[/dim]\n")
    task = input("👉 ")
    
    if not task.strip():
        console.print("\n❌ [bold red]Görev boş olamaz![/bold red]")
        sys.exit(1)
    
    return task.strip()


def run_agent_simple(task: str, api_key: str) -> dict:

    with sync_playwright() as p:
        headless = os.getenv("HEADLESS", "false").lower() == "true"
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            llm = GeminiLLM(api_key)
            tools = BrowserTools(page)
            agent = ReActAgent(llm, tools, max_iterations=10)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task(description="Agent çalışıyor...", total=None)
                result = agent.run(task)
            
            return result
            
        finally:
            browser.close()


def run_agent_with_langgraph(task: str, api_key: str) -> dict:
    with sync_playwright() as p:
        headless = os.getenv("HEADLESS", "false").lower() == "true"
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            llm = GeminiLLM(api_key)
            tools = BrowserTools(page)
            agent_graph = create_agent_graph(llm, tools, max_iterations=10)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task(description="LangGraph Agent çalışıyor...", total=None)
                result = agent_graph.run(task)
            
            return result
            
        finally:
            browser.close()


def print_result(result: dict):
    console.print("\n" + "="*60, style="bold blue")
    console.print("📊 [bold]SONUÇ RAPORU[/bold]", justify="center")
    console.print("="*60 + "\n", style="bold blue")
    
    if result["status"] == "PASSED":
        console.print(f"✅ Durum: [bold green]{result['status']}[/bold green]")
    else:
        console.print(f"❌ Durum: [bold red]{result['status']}[/bold red]")
    
    console.print(f"🔄 İterasyon: [cyan]{result.get('iterations', 'N/A')}[/cyan]")
    
    console.print(f"\n💬 [bold]Açıklama:[/bold]")
    console.print(Panel(Text(result["message"]), border_style="dim"))
    
    if result.get("execution_trace"):
        console.print(f"\n📜 [bold]Execution Trace:[/bold]")
        trace_text = "\n".join(result["execution_trace"][-20:])
        console.print(Panel(Text(trace_text), border_style="dim", expand=False))
    
    console.print("\n" + "="*60 + "\n", style="bold blue")


def main():
    try:
        print_banner()
        
        api_key = validate_env()
        console.print("✅ [green]API Key doğrulandı[/green]\n")
        
        task = get_user_task()
        
        console.print("\n🔧 [bold]Çalışma Modu:[/bold]")
        console.print("1. Basit ReAct Döngüsü")
        console.print("2. LangGraph ile (Önerilen)")
        
        mode = input("\n👉 Seçiminiz (1/2) [varsayılan: 2]: ").strip() or "2"
        
        console.print("\n🚀 [bold green]Agent başlatılıyor...[/bold green]\n")
        
        if mode == "1":
            result = run_agent_simple(task, api_key)
        else:
            result = run_agent_with_langgraph(task, api_key)
        
        print_result(result)
        
        return 0 if result["status"] == "PASSED" else 1
        
    except KeyboardInterrupt:
        console.print("\n\n⚠️  [yellow]Kullanıcı tarafından iptal edildi[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n\n❌ [bold red]HATA:[/bold red] {str(e)}")
        console.print("\n[dim]Detaylı hata için tekrar çalıştırın[/dim]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
