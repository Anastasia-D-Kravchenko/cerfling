# LinkedIn University Course Importer (GUI Edition)

The **LinkedIn University Course Importer** is a specialized automation tool designed to bridge the gap between your academic curriculum and your professional LinkedIn profile. By leveraging high-speed Llama models via the Groq API and intelligent browser automation, this application transforms a raw university curriculum PDF into structured professional entries on your profile.

---

### 🌟 Intelligent Automation Strategy
The application operates through a streamlined three-phase pipeline:

1.  **AI Curriculum Parsing:** * Uses `PyMuPDF` (`fitz`) to extract text from complex university curriculum documents.
    * Leverages `Groq` AI (Llama 3.3 70B) to parse raw text into structured JSON data, identifying specific Course Names and Course Numbers.
2.  **Browser Stealth & Security:**
    * Utilizes `undetected_chromedriver` to bypass aggressive automated browser detection during the injection process.
    * Maintains a persistent Chrome profile (`linkedin_chrome_profile`) to securely store authentication cookies, preventing the need for repeated logins.
3.  **Automated Field Injection:**
    * Automatically navigates to LinkedIn's hidden "Add Course" entry points.
    * Precisely fills Course Names, Numbers, and handles the dynamic "Associated with" dropdown to link the courses to your specific degree.

---

### 🛠 Technical Architecture
* **Multithreaded Interface:** Powered by `tkinter`, the GUI runs the automation engine in a separate background thread. This ensures the desktop application remains responsive and does not freeze while the browser is active.
* **Virtual Console:** A built-in "Activity Log" uses a custom `PrintRedirector` to funnel real-time system status and AI extraction logs directly into the window.
* **Local Persistence:** A `course_config.json` system automatically remembers your Groq API keys, PDF paths, and degree details for one-click resumes.

---

### 🚀 Setup & Execution
Install the necessary library ecosystem via your terminal:
```bash
pip install groq PyMuPDF selenium undetected-chromedriver
```

#### **How to Run:**
1.  **Launch:** Execute `python app.py` to open the GUI.
2.  **Configure:** * Enter your **Groq API Key** (obtainable at [console.groq.com](https://console.groq.com)).
    * **Browse** and select your curriculum PDF.
    * Input the **Degree Text** exactly as it appears in your LinkedIn profile dropdown (e.g., "Student at Polish-Japanese Academy").
3.  **Authenticate:** On the first run, a Chrome window will appear for manual LinkedIn login. Once you see your feed, click "OK" on the application popup to begin the batch import.

---

### ⚠️ Performance Notes
* **Anti-Bot Safety:** The bot includes a 4-second delay between course entries to simulate human behavior and avoid rate-limiting.
* **Headless Warning:** Headless mode is disabled by default to ensure the bot can successfully navigate LinkedIn’s dynamic modals and handle potential security checks.