# LinkedIn Certification Bot (GUI Edition)

A fully interactive desktop application that reads PDF certificates from a local folder, uses AI Vision to extract the data, and automatically adds them to your LinkedIn profile.

It features a clean `tkinter` graphical interface, saves your configurations locally, and processes your PDFs without leaving junk files on your machine.

## Features
* **Interactive UI:** No need to edit code. Just paste your API key, browse for your folder, and click Start.
* **AI Data Extraction:** Uses Groq Vision (Llama) to instantly read PDF certificates and convert them to structured JSON data (Name, Date, Organization, Skills).
* **In-Memory Processing:** Converts PDFs to images entirely in RAM using PyMuPDF.
* **Two-Phase LinkedIn Injection:** * Phase 1: Pre-fills the LinkedIn URL API to create the base certificate.
  * Phase 2: Automatically re-opens the entry to link the Company Logo and select related Skills from LinkedIn's dynamic dropdowns.
* **Anti-Bot Stealth:** Uses `undetected_chromedriver` to bypass LinkedIn's strict automated browser detection.

---

## 🛠 Prerequisites

You will need **Python 3.8+** installed on your system.

Install the required dependencies via terminal:
```bash
pip install groq PyMuPDF selenium undetected-chromedriver
```

You also need a **free API Key from Groq** to process the images:
1. Go to [console.groq.com](https://console.groq.com)
2. Create an account and generate an API key.

---

##  How to Run

1. Open your terminal or command prompt in the project folder.
2. Run the application:
   ```bash
   python app.py
   ```
3. **Fill out the UI:**
   * Paste your Groq API Key.
   * Click "Browse..." to select the folder containing your PDF certificates.
   * Add your GitHub raw URL base (e.g., `https://github.com/Username/Repo/blob/main/certs/`).
4. Click **START AUTOMATION**.

### The First Run (Authentication)
If this is your first time running the app, Chrome will open to the LinkedIn login page. 
* The app will pause for 30 seconds.
* Log in manually and solve any security captchas.
* The app saves your session securely to a local `linkedin_chrome_profile` folder. You will not need to log in again on future runs!

---

## Notes on Headless Mode
The app includes a checkbox to run "Headless" (invisible). 
* **Warning:** LinkedIn's anti-bot detection is highly aggressive against headless browsers. If the script fails to find elements or times out, it is likely because LinkedIn is throwing an invisible Captcha. 
* It is recommended to run the app with the browser visible so you can watch the magic happen!