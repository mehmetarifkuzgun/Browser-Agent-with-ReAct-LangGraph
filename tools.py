from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from typing import Dict, Any
import os


class BrowserTools:
    
    def __init__(self, page: Page):
        self.page = page
        self.timeout = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    
    def click(self, selector: str) -> Dict[str, Any]:
        try:
            self.page.wait_for_selector(selector, timeout=self.timeout)
            self.page.click(selector)
            return {
                "success": True,
                "message": f"'{selector}' elementine başarıyla tıklandı",
                "action": f"CLICK('{selector}')"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "message": f"Timeout: '{selector}' elementi {self.timeout}ms içinde bulunamadı",
                "action": f"CLICK('{selector}')"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Click hatası: {str(e)}",
                "action": f"CLICK('{selector}')"
            }
    
    def fill(self, selector: str, text: str) -> Dict[str, Any]:
        try:
            self.page.wait_for_selector(selector, timeout=self.timeout)
            self.page.fill(selector, text)
            return {
                "success": True,
                "message": f"'{selector}' alanına '{text}' başarıyla girildi",
                "action": f"FILL('{selector}', '{text}')"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "message": f"Timeout: '{selector}' elementi {self.timeout}ms içinde bulunamadı",
                "action": f"FILL('{selector}', '{text}')"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Fill hatası: {str(e)}",
                "action": f"FILL('{selector}', '{text}')"
            }
    
    def select(self, selector: str, value: str) -> Dict[str, Any]:
        try:
            self.page.wait_for_selector(selector, timeout=self.timeout)
            self.page.select_option(selector, value)
            return {
                "success": True,
                "message": f"'{selector}' dropdown'ından '{value}' başarıyla seçildi",
                "action": f"SELECT('{selector}', '{value}')"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "message": f"Timeout: '{selector}' elementi {self.timeout}ms içinde bulunamadı",
                "action": f"SELECT('{selector}', '{value}')"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Select hatası: {str(e)}",
                "action": f"SELECT('{selector}', '{value}')"
            }
    
    def verify_text(self, selector: str, expected: str) -> Dict[str, Any]:
        try:
            self.page.wait_for_selector(selector, timeout=self.timeout)
            actual_text = self.page.text_content(selector)
            
            if actual_text and expected.lower() in actual_text.lower():
                return {
                    "success": True,
                    "message": f"VERIFY PASSED: '{expected}' metni '{selector}' içinde bulundu",
                    "action": f"VERIFY_TEXT('{selector}', '{expected}')",
                    "verified": True
                }
            else:
                return {
                    "success": False,
                    "message": f"VERIFY FAILED: Beklenen '{expected}', bulunan '{actual_text}'",
                    "action": f"VERIFY_TEXT('{selector}', '{expected}')",
                    "verified": False
                }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "message": f"Timeout: '{selector}' elementi {self.timeout}ms içinde bulunamadı",
                "action": f"VERIFY_TEXT('{selector}', '{expected}')",
                "verified": False
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Verify hatası: {str(e)}",
                "action": f"VERIFY_TEXT('{selector}', '{expected}')",
                "verified": False
            }
    
    def screenshot(self, path: str) -> Dict[str, Any]:
        try:
            if not os.path.isabs(path):
                screenshots_dir = os.path.join(os.getcwd(), "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                full_path = os.path.join(screenshots_dir, path)
            else:
                full_path = path
            
            print(f"\n[DEBUG] Screenshot alınıyor: {full_path}")
            
            self.page.screenshot(path=full_path)
            
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                print(f"[DEBUG] Screenshot başarıyla kaydedildi: {full_path} ({file_size} bytes)")
                return {
                    "success": True,
                    "message": f"✅ Ekran görüntüsü '{full_path}' olarak kaydedildi ({file_size} bytes)",
                    "action": f"SCREENSHOT('{path}')"
                }
            else:
                print(f"[DEBUG] HATA: Screenshot dosyası oluşturulamadı: {full_path}")
                return {
                    "success": False,
                    "message": f"❌ Screenshot dosyası oluşturulamadı: {full_path}",
                    "action": f"SCREENSHOT('{path}')"
                }
        except Exception as e:
            print(f"[DEBUG] Screenshot hatası: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"❌ Screenshot hatası: {str(e)}",
                "action": f"SCREENSHOT('{path}')"
            }
    
    def press_enter(self, selector: str) -> Dict[str, Any]:

        try:
            self.page.wait_for_selector(selector, timeout=self.timeout)
            self.page.press(selector, "Enter")
            return {
                "success": True,
                "message": f"'{selector}' elementine Enter tuşu başarıyla basıldı",
                "action": f"PRESS_ENTER('{selector}')"
            }
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "message": f"Timeout: '{selector}' elementi {self.timeout}ms içinde bulunamadı",
                "action": f"PRESS_ENTER('{selector}')"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Press Enter hatası: {str(e)}",
                "action": f"PRESS_ENTER('{selector}')"
            }
    
    def navigate(self, url: str) -> Dict[str, Any]:
        try:
            self.page.goto(url, timeout=self.timeout)
            return {
                "success": True,
                "message": f"'{url}' adresine başarıyla gidildi",
                "action": f"NAVIGATE('{url}')"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Navigate hatası: {str(e)}",
                "action": f"NAVIGATE('{url}')"
            }
    
    def wait(self, milliseconds: int) -> Dict[str, Any]:
        try:
            self.page.wait_for_timeout(milliseconds)
            return {
                "success": True,
                "message": f"{milliseconds}ms beklendi",
                "action": f"WAIT({milliseconds})"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Wait hatası: {str(e)}",
                "action": f"WAIT({milliseconds})"
            }
