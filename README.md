# The **LinkedIn Certification & Project Bot (GUI Edition)** 
is a robust automation tool designed to bridge the gap between your local professional achievements and your online LinkedIn profile. By combining GitHub API data, local PDF parsing, and Groq's high-speed Llama models, this application automates the tedious manual entry of professional milestones.

---

### 🌟 Advanced Multi-Core Logic
The application is built on a two-pronged automation strategy:

1.  **Certification Automated Entry:**
    * **In-Memory Parsing:** Uses `PyMuPDF` to convert local PDF certificates into images directly in RAM, ensuring no temporary image files clutter your machine.
    * **Vision AI Extraction:** Leverages `Groq` Vision models to instantly read certificates and generate structured JSON data including course names, issuing organizations, and dates.
2.  **GitHub Project Sync:**
    * **Deep Context Extraction:** Instead of relying on short repository names, the bot fetches your `README.md` files from GitHub to provide Groq with full project context.
    * **AI Copywriting:** Automatically transforms basic repo metadata into professional, 2000-character LinkedIn summaries that highlight technical impact.
    * **Dynamic Skill Mapping:** Intelligently maps repository languages and documentation to LinkedIn’s internal skill taxonomy.

---

### 🛠 Technical Architecture
* **Interface:** Powered by `tkinter`, providing a clean desktop GUI that handles complex background threading to prevent application freezing during browser automation.
* **Persistence:** A local `config.json` system stores your API keys and GitHub tokens securely, allowing for one-click resumes.
* **Browser Stealth:** Utilizes `undetected_chromedriver` to bypass automated browser detection, allowing the script to navigate LinkedIn's dynamic modals as if it were a human user.
* **Logging:** A built-in virtual terminal ("Activity Log") provides real-time feedback on AI extraction and browser steps.

---

### 🚀 Setup & Dependency Management
To initialize your environment, install the necessary library ecosystem:
```bash
pip install groq PyMuPDF selenium undetected-chromedriver requests
```

#### **Core Configuration Requirements:**
* **Groq API:** Obtain a high-speed inference key at [console.groq.com](https://console.groq.com).
* **LinkedIn Authentication:** The bot uses a persistent Chrome profile (`linkedin_chrome_profile`). On your first run, the GUI will pause and prompt you to log in manually; subsequent runs will remain authenticated.

---

### ⚠️ Performance & Safety Notes
* **Headless vs. Visible:** While the app supports "Headless" mode for background work, running in visible mode is recommended for your first batch to handle LinkedIn's aggressive bot-detection challenges.
* **API Throttling:** For GitHub users with high repository counts (60+), the bot includes a Personal Access Token field to bypass GitHub's 60-request-per-hour anonymous limit.