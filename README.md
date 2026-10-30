# Instagram DM Tool - Unlimited Pagination & Working Unsend

A Python tool using [instagrapi](https://github.com/subzeroid/instagrapi) to:
- Log in to Instagram with session persistence (supports Username/Password, 2FA, and Browser Session ID)
- **Account-Wide Cleanup:** Scan across **ALL conversations in your inbox** and bulk unsend scam links, photos, and messages with 1 click
- Browse and scroll through your entire inbox history with interactive Next-Page pagination
- View unlimited messages in any thread with proper cursor-based pagination
- Search and filter messages by **All Messages**, **Keywords**, **Photos & Media**, **Links & URLs**, or **Recent Date Range**
- **Bulk unsend** your own messages, scam links, photos, videos, and disappearing snaps

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
   2. List Conversations (Browse Inbox with Next-Page pagination)
   3. Select Conversation (by Username or Thread ID)
   4. View Messages (Unlimited pagination in selected conversation)
   5. Search / Filter Messages (In selected conversation)
   6. Unsend Queued Messages (In selected conversation)
   7. CLEAN ALL CONVERSATIONS (Account-Wide Scam Unsend) [NEW]
   8. Logout / Switch Account
   9. Exit
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

### Step 6: Account-Wide Scam Cleanup (Option 7 - RECOMMENDED FOR HACKED ACCOUNTS)

> [!IMPORTANT]
> If your account was hacked and the scammer messaged **many people or everyone in your inbox**, use **Option 7**!
> You do **not** need to manually select or scroll through conversations one by one!

1. Select **Option 7: CLEAN ALL CONVERSATIONS (Account-Wide Scam Unsend)**.
2. **Choose how many conversations to scan:**
   - 1. Recent 25 conversations
   - 2. Recent 50 conversations
   - 3. Recent 100 conversations
   - 4. **ALL conversations in inbox (Full inbox scan)**
3. **Choose what to unsend:**
   - **1. ALL messages & media sent by you:** Unsends everything your account sent.
   - **2. Only Links & URLs:** Unsends all scam websites and links.
   - **3. Only Photos & Videos:** Unsends all scam photos, disappearing snaps, and media.
   - **4. Keywords:** Unsends messages containing words like `vote,link,gift,crypto`.
4. **Choose Date Range (Protects your older messages):**
   - Enter `3` or `7` to only delete messages sent in the last 3 or 7 days during the hack.
   - Or press Enter to scan all time.
5. Review the summary of found messages across all conversations.
6. Type `YES` to confirm. The tool will unsend all of them automatically across every conversation!

---

### Step 7: Cleaning a Single Conversation (Options 2, 5, 6)

If you only need to clean up a specific conversation:

#### Step 7.1: Select the Conversation
- **Option 2 (Browse Inbox):** Lists conversations 20 at a time. Type `N` to load the next 20 conversations and scroll down through your inbox, or enter the number of the conversation to select it.
- **Option 3 (Select by Username):** Enter the Instagram username directly.

#### Step 7.2: Filter Messages
1. Type `5` and press Enter (**Search / Filter Messages**).
2. Choose:
   - `1` for all messages sent by you.
   - `2` for keywords.
   - `3` for photos & videos.
   - `4` for links & URLs.
3. Enter how many messages in the chat history to scan (e.g. `1000`, `5000`, or more). The tool uses proper cursor pagination to traverse older message history.

#### Step 7.3: Unsend
1. Type `6` and press Enter (**Unsend Queued Messages**).
2. Type `YES` to confirm.

---

## 🎯 Common Use Cases

### Recovering from a Hacked Account (Account-Wide Cleanup)
1. Log in using your browser's **Session ID** (Option 1 -> Method 2).
2. Select **Option 7 (CLEAN ALL CONVERSATIONS)**.
3. Choose `4` (ALL conversations in inbox) or `3` (100 conversations).
4. Choose `1` (ALL messages sent by you) or `2` (Links & URLs) or `3` (Photos & Videos).
5. (Optional) Enter `3` for the last 3 days to protect older personal chats.
6. Confirm with `YES` and let the tool automatically unsend all scam content from all chats!

---

## ❓ FAQ & Troubleshooting

### Problem: "Your version of Instagram is out of date. Please upgrade your app to log in to Instagram." (`needs_upgrade`)
**Solution:**
Use **Session ID Cookie Login** (Option 1 -> Method 2). Browser cookies bypass mobile app client version deprecations and checkpoint challenges completely.

### Problem: "It only scans through head history not the whole sent messages"
**Solution:**
The latest update includes:
1. **Option 7 (Account-Wide Cleanup):** Paginates through your entire inbox and cleans all conversations automatically.
2. **Inbox Pagination (Option 2):** Type `N` to page down through older conversations in your inbox.
3. **Deep Thread Pagination (Option 4 & 5):** Fixed cursor pagination parameters (`seq_id="40065"`, `limit="20"`, `oldest_cursor`, and `MINCURSOR` detection) so searching deeply within a conversation can load thousands of older messages.

### Problem: Two-Factor Authentication (2FA) is enabled
**Solution:**
You do **not** need to disable 2FA! The tool prompts for your 6-digit verification code, or you can log in with Session ID (Method 2) to bypass 2FA entirely.

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
