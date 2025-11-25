# 🎬 KissKH Downloader: Simple Guide to Downloading Full Series

Welcome! This is a simple **Python** program that helps you download full drama series from KissKH directly to your computer.

It is designed to be **fast, reliable, and easy to use**, even if you've never used code before.

## 🚨 IMPORTANT: What You Need First

Before you can run this program, you need to install three essential tools on your computer.

| Tool | Purpose | 🔗 Download Link |
| :--- | :--- | :--- |
| **Python** | This is the language the program is written in. | **[Download Python (Official Site)](https://www.python.org/downloads/)** |
| **yt-dlp** | The program that actually downloads the video files. | **[Download yt-dlp.exe (GitHub)](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe)** |
| **FFmpeg** | This tool helps assemble the video chunks into a single .mp4 file. | **[Download FFmpeg (Gyan Dev Builds)](https://www.gyan.dev/ffmpeg/builds/#release-builds)** |

**Step 1.1: Install Python**
1.  Click the **Python Download Link** above and install the program.
2.  **CRITICAL STEP:** During installation, make sure you check the box that says **"Add python.exe to PATH"** or **"Add Python to Environment Variables."**

**Step 1.2: Download Helper Tools**
1.  Click the download links for **yt-dlp.exe** and **FFmpeg**.
2.  Create a new, simple folder on your computer (e.g., C:\Download_Tools).
3.  Place the yt-dlp.exe file and the fmpeg.exe file inside this C:\Download_Tools folder.

---

## 🚀 Setup Guide: Running the Downloader

### Step 2: Set Up the Project

1.  **Open PowerShell:** Find the search bar on your computer (usually bottom-left) and type PowerShell. Click the result to open it.
2.  **Navigate to Project:** Use the cd command to enter the folder where you saved this program. (Example: If you saved the program in a folder called KissKH-Downloader on your Desktop, you would type: cd Desktop\KissKH-Downloader)

3.  **Install Necessary Files:** We need to create a secure, isolated space for the program to run. Copy and paste these lines one at a time and press Enter:
    `ash
    # Create the virtual environment (the isolated space)
    python -m venv .venv

    # Activate the isolated space (you should see (.venv) at the start of your line)
    .venv\Scripts\activate

    # Install the program's required Python files
    pip install -r requirements.txt
    `

### Step 3: Configure and Run

1.  **Configure Tool Path:** Open the **kisskh_downloader.py** file using a text editor (like Notepad or VS Code). You need to change the path inside the code to match the folder you created in Step 1.2.

    Find the line that looks like this (around line 14):
    `python
    DOWNLOADER_PATH = r"C:\Users\YOUR_USER_NAME\YOUR_TOOLS_FOLDER"
    `
    Change it to your actual folder path:
    `python
    DOWNLOADER_PATH = r"C:\Download_Tools"
    `

2.  **Execute the Downloader:** Now run the program!
    `ash
    python kisskh_downloader.py
    `

### Step 4: Example of a Successful Run

When prompted, paste the **full Episode 1 URL** of the drama you wish to download.

**Input URL:** https://kisskh.co/Drama/Squid-Game-Season-3/Episode-1?id=10124&ep=172930&page=0&pageSize=100

**Example Output:**
