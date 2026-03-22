import os
import json
import time
import requests
import threading
import sys
import io
import tkinter as tk
from tkinter import scrolledtext, messagebox

from groq import Groq
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc

CONFIG_FILE = "config.json"
CHROME_PROFILE_DIR = os.path.abspath("linkedin_chrome_profile")


# ==========================================
# 1. CORE LOGIC (Adapted for GUI parameters)
# ==========================================

def fetch_github_projects(username, token):
    print(f"[*] Fetching public repositories for GitHub user: {username}...")
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
    headers = {"Authorization": f"token {token}"} if token else {}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"[-] Failed to fetch GitHub data. Status code: {response.status_code}")
        return []

    repos = response.json()
    projects = []
    for repo in repos:
        if repo.get("fork"):
            continue
        projects.append({
            "name": repo.get("name"),
            "clean_name": repo.get("name").replace("-", " ").replace("_", " ").title(),
            "description": repo.get("description") or "No description provided.",
            "language": repo.get("language") or "Various",
            "url": repo.get("html_url")
        })
    print(f"[+] Found {len(projects)} original projects on GitHub.")
    return projects


def fetch_readme(username, repo_name, token):
    url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    return "No README file available for this repository."


def generate_linkedin_project_data(repo_data, readme_content, groq_key):
    print(f"  [*] Using Groq to write summary for '{repo_data['clean_name']}'...")
    client = Groq(api_key=groq_key)
    truncated_readme = readme_content[:3000] if readme_content else ""

    prompt = f"""
    You are an expert tech resume writer. I need to add a project to my LinkedIn profile based on a GitHub repository.
    GitHub Repo Name: {repo_data['clean_name']}
    Short Description: {repo_data['description']}
    Main Language: {repo_data['language']}
    URL: {repo_data['url']}
    README.md Content:
    '''
    {truncated_readme}
    '''
    Based on the information above, create a JSON output with:
    - "name": (Cleaned up, professional project name)
    - "description": (Professional, impressive 2-3 sentence summary. Include GitHub URL at the end. Max 2000 chars.)
    - "skills": (List of up to 5 relevant technical skills as strings)
    Return ONLY valid JSON. No markdown formatting.
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        json_str = completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        project_data = json.loads(json_str)
        print("  [+] Groq successfully generated project copy.")
        return project_data
    except Exception as e:
        print(f"  [-] Groq API Error: {e}")
        return None


def process_single_project(driver, wait, project_data):
    project_name = project_data.get("name", "")
    print(f"  [*] Navigating to LinkedIn to add: '{project_name}'...")
    driver.get("https://www.linkedin.com/in/me/details/projects/")
    time.sleep(4)

    try:
        add_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='/add-edit/PROJECT/']")))
        add_button.click()
    except Exception:
        print("  [-] Could not find the 'Add Project' button. Skipping.")
        return

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pe-edit-form-page__modal")))
    time.sleep(3)

    try:
        name_input = driver.find_element(By.CSS_SELECTOR, "input[id*='-title']")
        name_input.clear()
        name_input.send_keys(project_name)
    except Exception as e:
        print(f"  [-] Error filling name: {e}")

    try:
        desc_input = driver.find_element(By.CSS_SELECTOR, "textarea[id*='-description']")
        desc_input.clear()
        desc_input.send_keys(project_data.get("description", ""))
    except Exception as e:
        print(f"  [-] Error filling description: {e}")

    skills = project_data.get('skills', [])
    if skills:
        print("  [*] Adding Skills...")
        for skill in skills:
            driver.execute_script("document.querySelector('.artdeco-modal__content').scrollTop = 1000;")
            time.sleep(1)
            try:
                skill_btn = driver.find_element(By.CSS_SELECTOR, "button[data-test-typeahead-cta__button]")
                skill_btn.click()
                time.sleep(1.5)
                inputs = driver.find_elements(By.CSS_SELECTOR,
                                              "input.typeahead-cta__input, input[data-test-typeahead-cta__button-typeahead-trigger]")
                visible_inputs = [inp for inp in inputs if inp.is_displayed()]
                if visible_inputs:
                    skill_input = visible_inputs[-1]
                    skill_input.click()
                    skill_input.clear()
                    skill_input.send_keys(skill)
                    time.sleep(3)
                    skill_input.send_keys(Keys.DOWN)
                    time.sleep(0.5)
                    skill_input.send_keys(Keys.RETURN)
                    print(f"    [+] Added skill: {skill}")
                    time.sleep(1)
            except Exception:
                print(f"    [-] Failed to add skill '{skill}'.")
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

    print("  [*] Saving Project...")
    try:
        driver.execute_script("document.querySelector('.artdeco-modal__content').scrollTop = 3000;")
        time.sleep(1.5)
        save_btn = driver.find_element(By.CSS_SELECTOR, "button[data-view-name='profile-form-save']")
        save_btn.click()
        time.sleep(4)
        print(f"[+] '{project_name}' successfully added to LinkedIn!\n")
    except Exception as e:
        print(f"  [-] Error saving project: {e}")


# ==========================================
# 2. GUI APPLICATION (TKINTER)
# ==========================================

class PrintRedirector(io.StringIO):
    """Redirects print() statements to a Tkinter ScrolledText widget."""

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self):
        pass


class LinkedInProjectsBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GitHub to LinkedIn Projects Bot 🤖")
        self.geometry("650x700")
        self.configure(padx=20, pady=20)

        # Variables
        self.github_user_var = tk.StringVar()
        self.github_token_var = tk.StringVar()
        self.groq_key_var = tk.StringVar()

        self.load_config()
        self.create_widgets()

        # Redirect prints to the console widget
        sys.stdout = PrintRedirector(self.console)

    def create_widgets(self):
        # --- INPUT FIELDS ---
        tk.Label(self, text="GitHub Username:", font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Entry(self, textvariable=self.github_user_var, width=50).pack(fill="x", pady=(0, 10))

        tk.Label(self, text="GitHub Personal Access Token (Optional but recommended):",
                 font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Entry(self, textvariable=self.github_token_var, show="*", width=50).pack(fill="x", pady=(0, 10))

        tk.Label(self, text="Groq API Key:", font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Entry(self, textvariable=self.groq_key_var, show="*", width=50).pack(fill="x", pady=(0, 15))

        # --- BUTTONS ---
        self.run_btn = tk.Button(self, text="🚀 START AUTOMATION", font=("Arial", 12, "bold"), bg="green", fg="black",
                                 command=self.start_thread)
        self.run_btn.pack(fill="x", pady=(0, 20))

        # --- CONSOLE OUTPUT ---
        tk.Label(self, text="Activity Log:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.console = scrolledtext.ScrolledText(self, height=20, state='disabled', bg="#1e1e1e", fg="#00ff00",
                                                 font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.github_user_var.set(data.get("github_user", ""))
                    self.github_token_var.set(data.get("github_token", ""))
                    self.groq_key_var.set(data.get("groq_key", ""))
            except Exception:
                pass

    def save_config(self):
        data = {
            "github_user": self.github_user_var.get().strip(),
            "github_token": self.github_token_var.get().strip(),
            "groq_key": self.groq_key_var.get().strip()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)

    def start_thread(self):
        user = self.github_user_var.get().strip()
        groq_key = self.groq_key_var.get().strip()

        if not user or not groq_key:
            messagebox.showwarning("Missing Input", "GitHub Username and Groq API Key are required.")
            return

        self.save_config()
        self.run_btn.config(state="disabled", text="Running (Check Log)...")

        # Clear console
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)

        # Run bot in a background thread to prevent UI freezing
        thread = threading.Thread(target=self.run_bot)
        thread.daemon = True
        thread.start()

    def run_bot(self):
        username = self.github_user_var.get().strip()
        github_token = self.github_token_var.get().strip()
        groq_key = self.groq_key_var.get().strip()

        try:
            github_projects = fetch_github_projects(username, github_token)
            if not github_projects:
                print("[-] No projects found to process. Exiting.")
                return

            options = uc.ChromeOptions()
            options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            driver = uc.Chrome(options=options)
            wait = WebDriverWait(driver, 20)

            print("[*] Checking LinkedIn session...")
            driver.get("https://www.linkedin.com/feed/")
            time.sleep(4)

            if any(keyword in driver.current_url for keyword in ["login", "checkpoint", "signup"]):
                print("\n[!] Login required.")
                # We use a popup box instead of input() so the GUI user can click OK when done
                messagebox.showinfo(
                    "Manual Login Required",
                    "Please log in to LinkedIn in the Chrome window.\n\nOnce you are fully logged in and see your feed, click OK on this box to continue the automation."
                )
                print("[*] Continuing with saved session...\n")

            for i, repo in enumerate(github_projects, 1):
                print(f"==================================================")
                print(f"[*] Processing Repo {i}/{len(github_projects)}: {repo['clean_name']}")
                print(f"==================================================")

                readme_content = fetch_readme(username, repo['name'], github_token)
                linkedin_data = generate_linkedin_project_data(repo, readme_content, groq_key)

                if linkedin_data:
                    process_single_project(driver, wait, linkedin_data)
                    time.sleep(5)

            print("\n[*] All operations complete.")
            messagebox.showinfo("Success", "All projects have been processed successfully!")

        except Exception as e:
            print(f"[-] Fatal Pipeline Error: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        finally:
            try:
                driver.quit()
            except:
                pass
            # Re-enable the start button safely from the thread
            self.after(0, lambda: self.run_btn.config(state="normal", text="🚀 START AUTOMATION"))


if __name__ == "__main__":
    app = LinkedInProjectsBotApp()
    app.mainloop()