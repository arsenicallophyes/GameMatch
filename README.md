# GameMatch Development Setup

These instructions will guide you through setting up and running the Game Match web application on a **Windows** machine in a **development** environment. Redis will run inside an Ubuntu WSL instance.

---

## Prerequisites

1. **Windows 10/11** with **WSL (Windows Subsystem for Linux)** feature enabled:
2. Install **Ubuntu** from the Microsoft Store.
3. **Python 3.12+** installed on Windows.
4. **Redis** installed inside the Ubuntu WSL instance only.

---

## 1. Install and Start Redis in WSL Ubuntu

1. Launch **Ubuntu** from the Start menu.
2. Update package lists and install Redis:

   ```bash
   sudo apt update
   sudo apt install redis-server -y
   ```
3. Start the Redis server:

   ```bash
   sudo service redis-server start
   ```
4. **Keep this Ubuntu terminal window open** while you run the application.

---

## 2. Set Your Steam API Key and Flask SECRET\_KEY on Windows

The application expects both your Steam API key and Flask `SECRET_KEY` as **Windows** environment variables (not inside WSL).

1. Open a **Windows PowerShell**.
2. Set your keys persistently with:

   ```powershell
   setx STEAM_API_KEY "YOUR_STEAM_API_KEY_HERE"
   setx SECRET_KEY "YOUR_FLASK_SECRET_KEY_HERE"
   ```
3. Close and reopen any Windows terminals to apply the new variables.
4. Verify:

   ```powershell
   echo $Env:STEAM_API_KEY
   echo $Env:SECRET_KEY
   ```

   Both commands should display the values you set.

## 3. Clone Repository & Create Virtual Environment Clone Repository & Create Virtual Environment

1. Open a **Windows PowerShell** in your desired folder:

   ```powershell
   git clone https://github.com/arsenicallophyes/GameMatch.git
   cd GameMatch
   ```
2. Install Python dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

---

## 4. Configure & Run the Flask App

1. Ensure your Windows environment has:

   * `SECRETE_KEY` set (see step 2).
   * `STEAM_API_KEY` set (see step 2).
2. In the same PowerShell session, or Visual Studio Code run:

   ```powershell
   python main.py
   ```
3. Open your browser to:  `http://localhost:8000`

---

## Notes

* **Redis** runs in WSL (Ubuntu). Your Windows Flask app will connect on `localhost:6379` by default.
* This setup is for **development** only.
* You can stop Redis by closing Ubuntu.
