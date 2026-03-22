import os
import json
import time
import sys
import io
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog

import fitz
import requests
from groq import Groq
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc

CONFIG_FILE = "course_config.json"
CHROME_PROFILE_DIR = os.path.abspath("linkedin_chrome_profile")


def extract_courses_from_pdf(pdf_path, groq_key):
    print(f"[*] Reading PDF: {os.path.basename(pdf_path)}...")

    try:
        client = Groq(api_key=groq_key)
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        print("[*] Extracting courses using Groq AI...")
        prompt = """
        Analyze this university curriculum text. Extract every Course Name and its Course Number/Code.
        Format the output as a strict JSON list of objects:
        [
          {"name": "Object Oriented Programming", "number": "OOP1"},
          {"name": "Relational Databases", "number": "RDB2"}
        ]
        Return ONLY valid JSON. No markdown tags.
        """

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt + "\n\nText:\n" + full_text[:15000]}],
            temperature=0.1,
        )
        json_str = completion.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        courses = json.loads(json_str)
        print(f"[+] Successfully extracted {len(courses)} courses!")
        return courses

    except Exception as e:
        print(f"[-] AI Extraction Error: {e}")
        return []


def add_course_to_linkedin(driver, wait, course, degree_text):
    print(f"[*] Adding Course: {course.get('name', 'Unknown')} ({course.get('number', 'N/A')})")

    driver.get("https://www.linkedin.com/profile/add?startTask=COURSE_NAME")

    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pe-edit-form-page__content")))
        time.sleep(2)

        try:
            name_input = driver.find_element(By.CSS_SELECTOR, "input[id*='COURSE-'][id$='-name']")
            name_input.clear()
            name_input.send_keys(course.get('name', ''))
        except Exception as e:
            print("  [-] Could not type course name.")

        try:
            num_input = driver.find_element(By.CSS_SELECTOR, "input[id*='COURSE-'][id$='-number']")
            num_input.clear()
            num_input.send_keys(course.get('number', ''))
        except Exception as e:
            print("  [-] Could not type course number.")

        try:
            dropdown = driver.find_element(By.CSS_SELECTOR, "select[id*='COURSE-'][id$='-occupation']")
            dropdown.click()
            time.sleep(1)
            dropdown.send_keys(degree_text)
            dropdown.send_keys(Keys.RETURN)
        except Exception as e:
            print("  [-] Could not select associated degree.")

        try:
            save_btn = driver.find_element(By.CSS_SELECTOR, "button[data-view-name='profile-form-save']")
            save_btn.click()
            print(f"  [+] Saved successfully.")
        except Exception as e:
            print("  [-] Could not click save button.")

        time.sleep(3)

    except Exception as e:
        print(f"  [-] Error navigating modal: {e}")



class PrintRedirector(io.StringIO):

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def flush(self): pass


class LinkedInCoursesBotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LinkedIn University Course Importer 🎓")
        self.geometry("650x700")
        self.configure(padx=20, pady=20)

        self.groq_key_var = tk.StringVar()
        self.pdf_path_var = tk.StringVar()
        self.degree_text_var = tk.StringVar()

        self.load_config()
        self.create_widgets()

        sys.stdout = PrintRedirector(self.console)

    def create_widgets(self):
        tk.Label(self, text="Groq API Key:", font=("Arial", 10, "bold")).pack(anchor="w")
        tk.Entry(self, textvariable=self.groq_key_var, show="*", width=50).pack(fill="x", pady=(0, 15))

        tk.Label(self, text="Curriculum PDF File:", font=("Arial", 10, "bold")).pack(anchor="w")
        pdf_frame = tk.Frame(self)
        pdf_frame.pack(fill="x", pady=(0, 15))
        tk.Entry(pdf_frame, textvariable=self.pdf_path_var).pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(pdf_frame, text="Browse...", command=self.browse_file).pack(side="right")

        tk.Label(self, text="LinkedIn Degree Text (To match dropdown exactly):", font=("Arial", 10, "bold")).pack(
            anchor="w")
        tk.Label(self, text="Ex: Student at Polsko-Japońska Akademia", font=("Arial", 8, "italic"), fg="gray").pack(
            anchor="w")
        tk.Entry(self, textvariable=self.degree_text_var, width=50).pack(fill="x", pady=(0, 20))

        self.run_btn = tk.Button(self, text="🚀 START AUTOMATION", font=("Arial", 12, "bold"), bg="blue", fg="black",
                                 command=self.start_thread)
        self.run_btn.pack(fill="x", pady=(0, 20))

        tk.Label(self, text="Activity Log:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.console = scrolledtext.ScrolledText(self, height=15, state='disabled', bg="#1e1e1e", fg="#00ffff",
                                                 font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Curriculum PDF",
            filetypes=(("PDF Files", "*.pdf"), ("All Files", "*.*"))
        )
        if filename:
            self.pdf_path_var.set(filename)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.groq_key_var.set(data.get("groq_key", ""))
                    self.pdf_path_var.set(data.get("pdf_path", ""))
                    self.degree_text_var.set(data.get("degree_text", "Student at Polsko-Japońska Akademia"))
            except Exception:
                pass

    def save_config(self):
        data = {
            "groq_key": self.groq_key_var.get().strip(),
            "pdf_path": self.pdf_path_var.get().strip(),
            "degree_text": self.degree_text_var.get().strip()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f)

    def start_thread(self):
        groq_key = self.groq_key_var.get().strip()
        pdf_path = self.pdf_path_var.get().strip()
        degree_text = self.degree_text_var.get().strip()

        if not groq_key or not pdf_path or not degree_text:
            messagebox.showwarning("Missing Input", "Please fill out all fields and select a PDF.")
            return

        if not os.path.exists(pdf_path):
            messagebox.showerror("File Error", "The selected PDF file does not exist.")
            return

        self.save_config()
        self.run_btn.config(state="disabled", text="Running (Check Log)...")

        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)

        thread = threading.Thread(target=self.run_bot)
        thread.daemon = True
        thread.start()

    def run_bot(self):
        groq_key = self.groq_key_var.get().strip()
        pdf_path = self.pdf_path_var.get().strip()
        degree_text = self.degree_text_var.get().strip()

        try:
            courses = extract_courses_from_pdf(pdf_path, groq_key)
            if not courses:
                print("[-] No courses extracted. Exiting.")
                return

            options = uc.ChromeOptions()
            options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
            options.add_argument("--disable-blink-features=AutomationControlled")

            print("[*] Launching Chrome Browser...")
            driver = uc.Chrome(options=options)
            wait = WebDriverWait(driver, 15)

            print("[*] Checking LinkedIn session...")
            driver.get("https://www.linkedin.com/feed/")
            time.sleep(4)

            if any(keyword in driver.current_url for keyword in ["login", "checkpoint", "signup"]):
                print("\n[!] Login required.")
                messagebox.showinfo(
                    "Manual Login Required",
                    "Please log in to LinkedIn in the Chrome window.\n\nOnce you are fully logged in and see your feed, click OK on this box to continue."
                )
                print("[*] Continuing with saved session...\n")

            for i, course in enumerate(courses, 1):
                print(f"==================================================")
                print(f"[*] Processing Course {i}/{len(courses)}")
                print(f"==================================================")

                add_course_to_linkedin(driver, wait, course, degree_text)

                time.sleep(4)

            print("\n[*] All operations complete!")
            messagebox.showinfo("Success", f"Successfully processed {len(courses)} courses!")

        except Exception as e:
            print(f"[-] Fatal Pipeline Error: {e}")
            messagebox.showerror("Error", f"An error occurred:\n{e}")
        finally:
            try:
                driver.quit()
            except:
                pass
            self.after(0, lambda: self.run_btn.config(state="normal", text="🚀 START AUTOMATION"))


if __name__ == "__main__":
    app = LinkedInCoursesBotApp()
    app.mainloop()