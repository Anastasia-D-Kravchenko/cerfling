import os
import sys
import json
import time
import base64
import urllib.parse
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

from groq import Groq
import fitz
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc

CONFIG_FILE = "config.json"
CHROME_PROFILE_DIR = os.path.abspath("linkedin_chrome_profile")


# ==========================================
# 1. AI & AUTOMATION LOGIC
# ==========================================

def get_base64_image_from_pdf(pdf_path, log_cb):
    log_cb(f"  -> Reading PDF into memory: {os.path.basename(pdf_path)}")
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode('utf-8')


def extract_cert_info_with_groq(api_key, pdf_path, log_cb):
    log_cb("\n[*] Extracting certificate data using Groq Vision AI...")
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        log_cb(f"  [-] Groq API Initialization Error: {e}")
        return None

    base64_image = get_base64_image_from_pdf(pdf_path, log_cb)
    prompt = """
    Analyze this certificate and extract the information into a strict JSON format. 
    Use the following keys:
    - "name": (Name of the specific course or certification)
    - "organization": (Issuing organization)
    - "issue_month": (Month as a number 1-12)
    - "issue_year": (Year, e.g., 2026)
    - "credential_id": (Serial No. or Credential ID)
    - "skills": (List of 2-3 relevant skills as strings)
    Return ONLY valid JSON.
    """
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}],
            temperature=0.1,
        )
        response_text = completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        cert_data = json.loads(response_text)
        log_cb(f"  [+] Extracted: {cert_data.get('name')} from {cert_data.get('organization')}")
        return cert_data
    except Exception as e:
        log_cb(f"  [-] AI Extraction Error: {e}")
        return None


def process_single_certificate(driver, wait, cert_data, media_url, log_cb):
    log_cb(f"[*] PHASE 1: Creating base entry for '{cert_data.get('name')}'...")
    params = {
        "startTask": "CERTIFICATION_NAME", "name": cert_data.get("name", ""),
        "organizationName": cert_data.get("organization", ""), "issueYear": cert_data.get("issue_year", ""),
        "issueMonth": cert_data.get("issue_month", ""), "certId": cert_data.get("credential_id", ""),
        "certUrl": media_url
    }
    driver.get(f"https://www.linkedin.com/profile/add?{urllib.parse.urlencode(params)}")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "artdeco-modal__content")))
    time.sleep(5)
    driver.execute_script("document.querySelector('.artdeco-modal__content').scrollTop = 2000;")
    time.sleep(1)
    driver.execute_script("""
        let saveBtn = Array.from(document.querySelectorAll('button.artdeco-button--primary')).find(b => b.innerText.includes('Save'));
        if (saveBtn) saveBtn.click();
    """)
    time.sleep(4)

    cert_name = cert_data.get("name", "")
    log_cb(f"[*] PHASE 2: Navigating to Profile to Edit...")
    driver.get("https://www.linkedin.com/in/me/details/certifications/")
    time.sleep(5)

    found = driver.execute_script("""
        let certName = arguments[0];
        let targetSvg = Array.from(document.querySelectorAll('svg[aria-label]')).find(svg => svg.getAttribute('aria-label').includes('Edit certification ' + certName));
        if (targetSvg) { let link = targetSvg.closest('a'); if (link) { link.click(); return true; } }
        let fallbackLink = document.querySelector('a[href*="/add-edit/CERTIFICATION/"]');
        if (fallbackLink) { fallbackLink.click(); return true; }
        return false;
    """, cert_name)

    if not found:
        log_cb("  [-] Could not find the edit button. Skipping to next.")
        return

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "artdeco-modal__content")))
    time.sleep(3)

    org_name = cert_data.get("organization", "")
    if org_name:
        log_cb(f"  [*] Linking Organization logo for '{org_name}'...")
        try:
            inputs = [inp for inp in driver.find_elements(By.CSS_SELECTOR, "input[placeholder='Ex: Microsoft']") if
                      inp.is_displayed()]
            if inputs:
                org_input = inputs[-1]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", org_input)
                time.sleep(0.5)
                org_input.click()
                org_input.clear()
                time.sleep(0.5)
                org_input.send_keys(org_name)
                time.sleep(3)
                org_input.send_keys(Keys.DOWN)
                time.sleep(0.5)
                org_input.send_keys(Keys.RETURN)
                time.sleep(1)
        except Exception as e:
            log_cb(f"  [-] Failed to link organization logo. Error: {e}")

    skills = cert_data.get('skills', [])
    if skills:
        log_cb("  [*] Typing Skills...")
        for skill in skills:
            driver.execute_script("document.querySelector('.artdeco-modal__content').scrollTop = 1500;")
            time.sleep(1)
            driver.execute_script("""
                let btn = document.querySelector('button[data-test-typeahead-cta__button]') || document.querySelector('button.typeahead-cta_button');
                if (btn) btn.click();
            """)
            time.sleep(1.5)
            try:
                inputs = [inp for inp in driver.find_elements(By.CSS_SELECTOR,
                                                              "input.typeahead-cta__input, input[data-test-typeahead-cta__button-typeahead-trigger]")
                          if inp.is_displayed()]
                if inputs:
                    skill_input = inputs[-1]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", skill_input)
                    time.sleep(0.5)
                    skill_input.click()
                    skill_input.clear()
                    skill_input.send_keys(skill)
                    time.sleep(3.5)
                    skill_input.send_keys(Keys.DOWN)
                    time.sleep(0.5)
                    skill_input.send_keys(Keys.RETURN)
                    log_cb(f"    [+] Added: {skill}")
                    time.sleep(1)
            except Exception:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

    log_cb("  [*] Saving Updated Certification...")
    driver.execute_script("document.querySelector('.artdeco-modal__content').scrollTop = 2000;")
    time.sleep(1.5)
    driver.execute_script("""
        let saveBtn = Array.from(document.querySelectorAll('button.artdeco-button--primary')).find(b => b.innerText.includes('Save'));
        if (saveBtn) saveBtn.click();
    """)
    time.sleep(4)
    log_cb(f"[+] '{cert_name}' fully processed!\n")


def run_pipeline(api_key, cert_dir, github_url, headless, log_cb, on_complete):
    try:
        pdf_files = [f for f in os.listdir(cert_dir) if f.lower().endswith('.pdf')]
        if not pdf_files:
            log_cb("[-] No PDF files found in the directory.")
            return

        log_cb(f"[*] Found {len(pdf_files)} certificates to process.\n")

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        if headless: options.add_argument("--headless")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 20)

        log_cb("[*] Checking LinkedIn session...")
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(4)

        if any(kw in driver.current_url for kw in ["login", "checkpoint", "signup"]):
            log_cb("\n[!] No active session found. Please log in manually in the browser.")
            log_cb("[!] Waiting for user to complete login... Type 'ready' in the terminal or wait if not headless.")
            time.sleep(30)

        for i, pdf_file in enumerate(pdf_files, 1):
            log_cb(f"==================================================")
            log_cb(f"[*] Processing {i}/{len(pdf_files)}: {pdf_file}")
            log_cb(f"==================================================")

            pdf_path = os.path.join(cert_dir, pdf_file)
            media_url = github_url + urllib.parse.quote(pdf_file)

            cert_data = extract_cert_info_with_groq(api_key, pdf_path, log_cb)
            if cert_data:
                process_single_certificate(driver, wait, cert_data, media_url, log_cb)
                time.sleep(3)

        log_cb("\n[*] All operations complete!")
    except Exception as e:
        log_cb(f"[-] Pipeline Error: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
        on_complete()


# ==========================================
# 2. TKINTER GUI APP
# ==========================================

class LinkedInBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LinkedIn Certificate Auto-Adder 🎓")
        self.geometry("600x650")
        self.configure(padx=20, pady=20)
        self.api_key_var = tk.StringVar()
        self.cert_dir_var = tk.StringVar()
        self.github_url_var = tk.StringVar()
        self.headless_var = tk.BooleanVar(value=False)
        self.load_config()
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Groq API Key:", font=("Arial", 10, "bold"), anchor="w").pack(fill="x")
        tk.Entry(self, textvariable=self.api_key_var, show="*", width=50).pack(fill="x", pady=(0, 10))

        tk.Label(self, text="Certificates Folder (PDFs):", font=("Arial", 10, "bold"), anchor="w").pack(fill="x")
        dir_frame = tk.Frame(self)
        dir_frame.pack(fill="x", pady=(0, 10))
        tk.Entry(dir_frame, textvariable=self.cert_dir_var).pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(dir_frame, text="Browse...", command=self.browse_folder).pack(side="right")
        tk.Label(self, text="GitHub Base URL (Ends with /):", font=("Arial", 10, "bold"), anchor="w").pack(fill="x")
        tk.Entry(self, textvariable=self.github_url_var).pack(fill="x", pady=(0, 10))
        tk.Checkbutton(self, text="Run in Headless Mode (Invisible Browser)", variable=self.headless_var).pack(anchor="w", pady=(0, 15))
        self.run_btn = tk.Button(self, text="🚀 START AUTOMATION", font=("Arial", 12, "bold"), bg="green", fg="black", command=self.start_automation)
        self.run_btn.pack(fill="x", pady=(0, 20))
        tk.Label(self, text="Activity Log:", font=("Arial", 10, "bold"), anchor="w").pack(fill="x")
        self.console = scrolledtext.ScrolledText(self, height=15, state='disabled', bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.cert_dir_var.set(folder)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.api_key_var.set(data.get("api_key", ""))
                    self.cert_dir_var.set(data.get("cert_dir", ""))
                    self.github_url_var.set(data.get("github_url", ""))
            except:
                pass

    def save_config(self):
        data = {
            "api_key": self.api_key_var.get(),
            "cert_dir": self.cert_dir_var.get(),
            "github_url": self.github_url_var.get()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)

    def log(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.console.config(state='normal')
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.console.config(state='disabled')

    def start_automation(self):
        if not self.api_key_var.get() or not self.cert_dir_var.get():
            messagebox.showwarning("Missing Input", "Please provide the API Key and Folder path.")
            return

        self.save_config()
        self.run_btn.config(state="disabled", text="Running...")
        self.console.config(state='normal')
        self.console.delete(1.0, tk.END)
        self.console.config(state='disabled')

        self.log("[*] Starting automation thread...")

        thread = threading.Thread(target=run_pipeline, args=(
            self.api_key_var.get(),
            self.cert_dir_var.get(),
            self.github_url_var.get(),
            self.headless_var.get(),
            self.log,
            self.on_automation_complete
        ))
        thread.daemon = True
        thread.start()

    def on_automation_complete(self):
        self.after(0, lambda: self.run_btn.config(state="normal", text="🚀 START AUTOMATION"))


if __name__ == "__main__":
    app = LinkedInBotApp()
    app.mainloop()