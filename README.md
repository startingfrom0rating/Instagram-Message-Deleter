# 📸 Instagram Message Manager & Security Tool

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Maintained-success)

A powerful, modern CLI tool to manage your Instagram DMs, bulk unsend messages, and secure your account.  
Built with `instagrapi` and `rich` for a beautiful terminal experience.

![Demo](https://via.placeholder.com/800x400.png?text=Modern+CLI+Interface)

## ✨ Features

- **🚀 Bulk Unsend**: Scan **all** your conversations to find and unsend specific messages (e.g., photos, videos, or keywords).
- **🕵️ Login Activity Monitor**: View all active sessions, including device type, location, and IP address.
- **🛡️ Security Check**: Built-in heuristics to detect if third-party bots/apps are accessing your account.
- **🔍 Deep Search**: Pagination support to search through thousands of messages.
- **🎨 Modern UI**: Color-coded tables, progress bars, and interactive menus.
- **🔐 Privacy First**: Your password is never saved in the code (session caching is local only).

## 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/Instagram-Message-Deleter.git
   cd Instagram-Message-Deleter
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

Run the tool:

```bash
python instagram_dm_tool.py
```

### Menu Options

1. **Login**: Secure login with 2FA support.
2. **Bulk Unsend**: The main feature. Enter a keyword (e.g., `photo`, `video`, or a specific text) -> The tool scans all your chats -> Unsends matches automatically.
3. **View Login Activity**: See who is logged into your account.
4. **View Messages (Debug)**: Inspect raw message JSON to trace where messages originated (Mobile vs Bot).
5. **Security Advice**: Interactive guide to securing your account if compromised.

## ⚠️ Disclaimer

This tool is for **educational and personal use only**.

- Use responsibly. Excessive automated actions (like unsending 1000s of messages in seconds) may trigger Instagram's rate limits.
- The authors are not responsible for any account locks or bans.

## 📄 License

MIT License. Free to use and modify.
