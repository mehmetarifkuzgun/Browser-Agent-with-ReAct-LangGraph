import re
import os
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from tools import BrowserTools


class GeminiLLM:    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    def generate(self, prompt: str) -> str:

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"LLM ERROR: {str(e)}"


class ReActAgent:

    def __init__(self, llm: GeminiLLM, tools: BrowserTools, max_iterations: int = 3):
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations
        self.history: List[str] = []
        
    def parse_actions(self, llm_output: str) -> List[Tuple[str, List[str]]]:

        print(f"\n[DEBUG] parse_actions çağrıldı, input uzunluğu: {len(llm_output)}")
        print(f"[DEBUG] LLM output ilk 200 karakter: {llm_output[:200]}")
        
        actions = []
        
        action_pattern = r'ACTION:\s*(\w+)\((.*?)\)'
        matches = re.finditer(action_pattern, llm_output, re.IGNORECASE)
        
        for match in matches:
            action_name = match.group(1).upper()
            args_str = match.group(2)
            
            args = []
            arg_pattern = r'["\']([^"\']*)["\']'
            arg_matches = re.finditer(arg_pattern, args_str)
            for arg_match in arg_matches:
                args.append(arg_match.group(1))
            
            actions.append((action_name, args))
        
        return actions
    
    def execute_action(self, action_name: str, args: List[str]) -> Dict[str, Any]:
        print(f"\n[DEBUG] execute_action çağrıldı: {action_name}({args})")
        
        action_map = {
            "CLICK": lambda: self.tools.click(args[0]) if len(args) >= 1 else {"success": False, "message": "CLICK için selector gerekli"},
            "FILL": lambda: self.tools.fill(args[0], args[1]) if len(args) >= 2 else {"success": False, "message": "FILL için selector ve text gerekli"},
            "SELECT": lambda: self.tools.select(args[0], args[1]) if len(args) >= 2 else {"success": False, "message": "SELECT için selector ve value gerekli"},
            "VERIFY_TEXT": lambda: self.tools.verify_text(args[0], args[1]) if len(args) >= 2 else {"success": False, "message": "VERIFY_TEXT için selector ve expected gerekli"},
            "SCREENSHOT": lambda: self.tools.screenshot(args[0]) if len(args) >= 1 else {"success": False, "message": "SCREENSHOT için path gerekli"},
            "PRESS_ENTER": lambda: self.tools.press_enter(args[0]) if len(args) >= 1 else {"success": False, "message": "PRESS_ENTER için selector gerekli"},
            "NAVIGATE": lambda: self.tools.navigate(args[0]) if len(args) >= 1 else {"success": False, "message": "NAVIGATE için url gerekli"},
            "WAIT": lambda: self.tools.wait(int(args[0])) if len(args) >= 1 else {"success": False, "message": "WAIT için milliseconds gerekli"},
            "DONE": lambda: {"success": True, "message": "Görev tamamlandı", "action": "DONE()", "done": True},
        }
        
        if action_name in action_map:
            result = action_map[action_name]()
            print(f"[DEBUG] execute_action sonuç: success={result.get('success')}, message={result.get('message')}")
            return result
        else:
            result = {
                "success": False,
                "message": f"Bilinmeyen action: {action_name}",
                "action": f"{action_name}({', '.join(args)})"
            }
            print(f"[DEBUG] Bilinmeyen action: {action_name}")
            return result
    
    def build_prompt(self, user_task: str) -> str:
        system_prompt = """Sen bir browser otomasyon ajanısın. ReAct (Reasoning + Acting) yaklaşımını kullanarak görevleri tamamlarsın.

Kullanabileceğin ACTIONLAR:
- NAVIGATE("url"): Belirtilen URL'e git
- CLICK("selector"): CSS selector'a tıkla
- FILL("selector", "text"): Input alanına text yaz
- SELECT("selector", "value"): Dropdown'dan seçim yap
- VERIFY_TEXT("selector", "expected"): Text doğrula
- PRESS_ENTER("selector"): Enter tuşuna bas
- WAIT(milliseconds): Belirtilen süre bekle
- SCREENSHOT("path"): Ekran görüntüsü al
- DONE(): Görev tamamlandı, bitir

FORMAT:
1. THINK: Mevcut durumu analiz et ve bir sonraki adımı planla
2. ACTION: Yapılacak işlemi belirt (yukarıdaki formatlardan birini kullan)

Örnek:
THINK: Önce Google'a gitmem gerekiyor.
ACTION: NAVIGATE("https://www.google.com")

THINK: Arama kutusunu bulmak için yaygın selectorları denemeliyim. Google'da genellikle textarea[name='q'] veya input[name='q'] kullanılır.
ACTION: FILL("textarea[name='q']", "Python")

THINK: Arama için Enter'a basmalıyım.
ACTION: PRESS_ENTER("textarea[name='q']")

ÖNEMLİ SELECTOR İPUÇLARI:
- Google arama: textarea[name='q'], input[name='q'], input[title='Search']
- Amazon arama: input#twotabsearchtextbox, input[type='text'][placeholder*='Search']
- Genel arama kutuları: input[type='search'], input[placeholder*='ara'], input[placeholder*='Ara'], input[placeholder*='search'], textarea[name='q']
- Butonlar: button[type='submit'], button, input[type='submit']
- Linkler: a[href*='keyword']

ÖNEMLİ KURALLAR:
- Her seferinde SADECE BİR ACTION yaz
- Selector bulamazsan hata verir, o zaman alternatif selector dene
- Türkçe düşün ama ACTION komutlarını İngilizce formatında yaz
- Önce NAVIGATE ile sayfaya git, sonra WAIT(2000) ile sayfanın yüklenmesini bekle
- Sonra diğer işlemleri yap
- Görev tamamlandıktan sonra SCREENSHOT ile ekran görüntüsü alarak kanıtla
- VERIFY_TEXT ile doğrulama yap
- Tüm işlemler bittikten sonra DONE() ile bitir
"""
        
        history_str = ""
        if self.history:
            history_str = "\n\n=== ÖNCEKİ ADIMLAR ===\n" + "\n".join(self.history[-10:])  # Son 10 adım
        
        prompt = f"""{system_prompt}

=== GÖREV ===
{user_task}
{history_str}

Şimdi bir sonraki adımı planla ve ACTION komutunu ver:
"""
        return prompt
    
    def run(self, user_task: str) -> Dict[str, Any]:

        self.history = []
        self.history.append(f"=== GÖREV: {user_task} ===")
        
        completed_iterations = 0
        verification_passed = False
        screenshot_taken = False
        task_done = False
        
        for iteration in range(self.max_iterations):
            completed_iterations = iteration + 1
            self.history.append(f"\n--- İTERASYON {iteration + 1} ---")
            
            prompt = self.build_prompt(user_task)
            llm_output = self.llm.generate(prompt)
            
            self.history.append(f"LLM OUTPUT:\n{llm_output}")
            
            actions = self.parse_actions(llm_output)
            
            if actions:
                print(f"\n[DEBUG] Parse edilen {len(actions)} action:")
                for action_name, args in actions:
                    print(f"  - {action_name}({', '.join(repr(arg) for arg in args)})")
            else:
                print(f"\n[DEBUG] Hiçbir ACTION parse edilemedi!")
            
            if not actions:
                self.history.append("OBSERVATION: LLM'den geçerli ACTION bulunamadı, tekrar deneniyor...")
                if verification_passed and screenshot_taken:
                    break
                continue
            
            for action_name, args in actions:
                result = self.execute_action(action_name, args)
                
                observation = f"OBSERVATION: {result['message']}"
                self.history.append(observation)
                
                if action_name == "VERIFY_TEXT" and result.get("verified", False):
                    verification_passed = True
                
                if action_name == "SCREENSHOT" and result.get("success", False):
                    screenshot_taken = True
                
                if action_name == "DONE" and result.get("done", False):
                    task_done = True
                    self.history.append("\n✅ LLM görevi tamamlandı olarak işaretledi")
                    break
            
            if task_done or (verification_passed and screenshot_taken):
                if not task_done:
                    self.history.append("\n✅ Görev başarıyla tamamlandı (verification geçti ve screenshot alındı)")
                break
        
        return self.evaluate_run(success=verification_passed if verification_passed else None, iterations=completed_iterations)
    
    def evaluate_run(self, success: bool = None, iterations: int = None) -> Dict[str, Any]:
        if success is not None:
            status = "PASSED" if success else "FAILED"
        else:
            history_text = "\n".join(self.history)
            if "VERIFY PASSED" in history_text:
                status = "PASSED"
            else:
                status = "FAILED"
        
        last_observations = [line for line in self.history if line.startswith("OBSERVATION:")][-10:]
        
        if last_observations:
            message = f"Agent çalışması tamamlandı ({iterations or self.max_iterations} iterasyon).\n\nSon durumlar:\n" + "\n".join(last_observations)
        else:
            message = f"Agent çalışması tamamlandı ({iterations or self.max_iterations} iterasyon). Observation bulunamadı."
        
        return {
            "status": status,
            "message": message,
            "execution_trace": self.history,
            "iterations": iterations or self.max_iterations
        }
