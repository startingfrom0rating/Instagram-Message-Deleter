# Instagram DM Tool - Unlimited Pagination & Working Unsend

A Python tool using [instagrapi](https://github.com/subzeroid/instagrapi) to:
- Log in to Instagram with session persistence (supports Username/Password, 2FA, and Browser Session ID)
- List and select DM conversations
- View unlimited messages (cursor-based pagination)
- Search and filter messages by **All Messages**, **Keywords**, **Photos & Media**, or **Links & URLs**
- **Bulk unsend** your own messages, scam links, photos, and media

---

## ⚠️ Disclaimer
This tool interacts with Instagram's private APIs and may violate Instagram's Terms of Service.  
**Use at your own risk.** Your account may be subject to temporary or permanent restrictions.

---

## 📚 Complete Beginner's Tutorial

This guide will walk you through everything you need to know, even if you've never coded before!

### Step 1: Install Python

Python is the programming language this tool is written in. You need to install it first.

#### For Windows:
1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click the yellow "Download Python 3.x.x" button
3. Run the installer
4. **IMPORTANT**: Check the box that says "Add Python to PATH" at the bottom
5. Click "Install Now"
6. Wait for installation to complete

#### For Mac:
1. Open Terminal (press Cmd+Space, type "Terminal", press Enter)
2. Install Homebrew if you don't have it:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Install Python:
   ```bash
   brew install python3
   ```

#### For Linux (Ubuntu/Debian):
1. Open Terminal
2. Run these commands:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   ```

**Verify Python is installed:**
Open Terminal (or Command Prompt on Windows) and type:
```bash
python3 --version
```
You should see something like `Python 3.x.x`

---

### Step 2: Download This Tool

You have two options:

#### Option A: Download as ZIP (Easier for beginners)
1. Click the green "Code" button at the top of this GitHub page
2. Click "Download ZIP"
3. Extract the ZIP file to a folder you can find easily (like your Desktop or Documents)
4. Remember where you saved it!

#### Option B: Using Git
1. Open Terminal/Command Prompt
2. Navigate to where you want to save the tool:
   ```bash
   cd Desktop
   ```
3. Clone the repository:
   ```bash
   git clone https://github.com/startingfrom0rating/Instagram-Message-Deleter.git
   cd Instagram-Message-Deleter
   ```

---

### Step 3: Install Required Libraries

This tool needs `instagrapi` to connect to Instagram. Make sure you install or upgrade to the latest version to prevent "app out of date" errors:

1. Open Terminal/Command Prompt
2. Navigate to the folder where you saved this tool:
   ```bash
   cd path/to/Instagram-Message-Deleter
   ```
   Example on Windows: `cd C:\Users\YourName\Desktop\Instagram-Message-Deleter`  
   Example on Mac/Linux: `cd ~/Desktop/Instagram-Message-Deleter`

3. Install the required libraries:
   ```bash
   pip install --upgrade -r requirements.txt
   ```
   Or:
   ```bash
   pip install --upgrade instagrapi
   ```

---

### Step 4: Run the Tool

1. Make sure you're in the tool's folder (from Step 3)
2. Run the tool:
   ```bash
   python instagram_dm_tool.py
   ```
   (Or `python3 instagram_dm_tool.py` on Mac/Linux)

3. You will see the main menu:
   ```
   =======================================================
      INSTAGRAM DM TOOL - UNLIMITED PAGINATION & UNSEND
   =======================================================
   Status:   NOT LOGGED IN (Select Option 1 to connect)
   Thread:   None selected (Select Option 2 or 3)

   Options:
   1. Login / Account (Username/Password or Session ID Cookie)
   2. List Conversations (Raw API)
   3. Select Conversation (by Username or Thread ID)
   4. View Messages (Unlimited pagination)
   5. Search / Filter Messages (All, Keywords, Photos, Links)
   6. Unsend Queued Messages (Working)
   7. Logout / Switch Account
   8. Exit
   ```

---

### Step 5: Login to Instagram

Select **Option 1** from the menu. You can choose between two login methods:

#### Method 1: Username & Password (with 2FA)
- Standard login using your Instagram username and password.
- If you have **Two-Factor Authentication (2FA)** enabled, the tool will prompt you to enter your 6-digit SMS or Authenticator code. *(You do NOT need to disable 2FA!)*

#### Method 2: Browser Session ID Cookie (RECOMMENDED)
> [!TIP]
> **Use this if you get the "Instagram app out of date" error, a checkpoint challenge, or if your account was recently hacked/flagged!**
> This method bypasses mobile app login restrictions completely by using your active browser session.

**How to get your `sessionid`:**
1. Open https://www.instagram.com in your web browser (Chrome, Edge, Firefox, Brave, Safari) and make sure you are logged in.
2. Open Developer Tools:
   - **Chrome / Edge / Brave**: Press `F12` (or right-click anywhere -> **Inspect**) -> Click the **Application** tab -> expand **Cookies** on the left -> click `https://www.instagram.com`.
   - **Firefox**: Press `F12` -> Click **Storage** -> expand **Cookies** -> click `https://www.instagram.com`.
   - **Safari**: Preferences -> Advanced -> check "Show Develop menu", then right-click -> Inspect Element -> Storage -> Cookies.
3. Look for the cookie named **`sessionid`**.
4. Double-click its **Value** and copy the entire string.
5. In the tool, select **Option 1 -> Method 2**, paste your `sessionid`, and press Enter.

Your session is automatically saved to `session.json` so you stay logged in between runs!

---

### Step 6: Select a Conversation

You have two ways to pick the conversation you want to clean up:

#### Option A: List Recent Conversations
1. Type `2` and press Enter.
2. You will see a numbered list of your conversations with user names and latest message previews.
3. Type the number corresponding to the conversation and press Enter.

#### Option B: Select by Username
1. Type `3` and press Enter.
2. Type the Instagram username of the person whose conversation you want to open.
3. Press Enter.

---

### Step 7: Filter & Bulk Unsend Messages

#### Step 7.1: Filter Messages to Unsend
1. Type `5` and press Enter (**Search / Filter Messages**).
2. Choose what you want to target:
   - **1. ALL messages sent by you:** Unsend every single message, link, and photo sent from your account in this conversation (best for cleaning up after being hacked).
   - **2. Search by keyword(s):** Target specific words (e.g. `scam,crypto,gift,http`).
   - **3. Only Photos & Videos:** Targets all photos, videos, disappearing snaps, and shared media sent by you.
   - **4. Only Links & URLs:** Targets all scam links and websites sent by you.
3. Enter how many messages in the chat history to scan (default is 1000).
4. The tool scans backwards using cursor pagination and displays all matching messages.

#### Step 7.2: Unsend the Messages
1. Type `6` and press Enter (**Unsend Queued Messages**).
2. The tool displays:
   - How many messages from your account will be unsent.
   - A breakdown of texts, photos/media, and links.
   - A preview of the first 10 messages.
   - Confirmation that messages sent by other participants are safe and will *not* be deleted.
3. Type `YES` (in capital letters) to confirm.
4. The tool unsends each message one by one with a built-in 1-second delay to protect your account from spam detection.

---

## 🎯 Common Use Cases

### Recovering from a Hacked Account (Unsend Scam Links & Photos)
1. Log in using your browser's **Session ID** (Option 1 -> Method 2).
2. Select the conversation (Option 2 or 3).
3. Select **Option 5** -> choose **1** (ALL messages sent by you) or **4** (Only Links & URLs) or **3** (Only Photos & Videos).
4. Enter `5000` to scan through the full chat history.
5. Select **Option 6**, type `YES`, and let the tool unsend all the scam content!

### Delete All Messages in a Conversation
1. Select the conversation (Option 2 or 3).
2. Select **Option 5** -> **1. ALL messages sent by you**.
3. Enter a high number like `5000` or `10000`.
4. Select **Option 6** and type `YES`.

### Delete Specific Keywords Only
1. Select the conversation (Option 2 or 3).
2. Select **Option 5** -> **2. Search by keyword(s)**.
3. Enter comma-separated keywords (e.g. `password,secret,embarrassing`).
4. Select **Option 6** and confirm.

---

## ❓ FAQ & Troubleshooting

### Problem: "Your version of Instagram is out of date. Please upgrade your app to log in to Instagram." (`needs_upgrade`)
**Why this happens:**
Instagram's servers periodically deprecate older mobile app client signatures or flag third-party password logins from accounts/IPs that recently experienced suspicious activity (like being compromised or having a password changed).

**How to resolve it:**
1. **Best & Instant Solution:** Use **Session ID Cookie Login**!
   - In the tool, choose **Option 1 -> Method 2**.
   - Copy your `sessionid` cookie from your browser where you are logged in to [instagram.com](https://www.instagram.com) (press F12 -> Application -> Cookies -> `sessionid`).
   - Web sessions are immune to mobile client version checks.
2. **Upgrade instagrapi:**
   Make sure you have the newest version of `instagrapi` installed:
   ```bash
   pip install --upgrade instagrapi
   ```

### Problem: Two-Factor Authentication (2FA) is enabled
**Solution:**
You do **not** need to disable 2FA!
- When logging in with Username & Password (Method 1), the tool will detect 2FA and prompt you for your 6-digit code.
- Alternatively, logging in via **Session ID** (Method 2) bypasses 2FA prompts entirely.

### Problem: "UnicodeEncodeError: 'charmap' codec can't encode character" on Windows
**Solution:**
The latest update uses universal ASCII indicators (`[+]`, `[!]`, `[-]`) and automatically configures UTF-8 output on Windows consoles, preventing character encoding crashes.

### Q: Will this delete the other person's messages?
**A:** No. Instagram only allows unsending messages sent by your own account. The tool automatically protects and ignores messages sent by other chat participants.

### Q: Can photos, videos, and disappearing snaps be unsent?
**A:** Yes! The tool supports unsending text messages, direct photo/video uploads, disappearing snaps (`raven_media`), reels, and shared links.

### Q: How fast does it unsend?
**A:** The tool includes a 1-second delay between deletions to adhere to Instagram rate limits and prevent temporary account locks.

---

## 📋 Requirements
- Python 3.6+
- `instagrapi>=3.2.0` (install via `pip install --upgrade -r requirements.txt`)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
