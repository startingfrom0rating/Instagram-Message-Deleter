#!/usr/bin/env python3
"""
instagram_dm_tool.py
Instagram DM tool with PROPER PAGINATION using Instagram's cursor system.
Supports bulk unsend of text, links, photos, and media.
Supports Username/Password (with 2FA) and Session ID Cookie login (bypasses out-of-date error).
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Check Python version
if sys.version_info < (3, 6):
    print("ERROR: Python 3.6 or higher required")
    sys.exit(1)

# Ensure stdout/stderr handle UTF-8 or fallback gracefully on Windows cp1252 consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    from instagrapi import Client
    try:
        from instagrapi.exceptions import (
            TwoFactorRequired,
            ChallengeRequired,
            ClientNeedsUpgradeError,
            BadPassword,
            BadCredentials,
            LoginRequired,
            ClientError
        )
    except ImportError:
        from instagrapi.exceptions import (
            TwoFactorRequired,
            ChallengeRequired,
            BadPassword,
            LoginRequired,
            ClientError
        )
        class ClientNeedsUpgradeError(Exception):
            pass
        class BadCredentials(Exception):
            pass

    print("[+] instagrapi imported successfully")
except ImportError as e:
    print(f"ERROR: instagrapi not installed: {e}")
    print("Install or upgrade with: pip install --upgrade instagrapi")
    sys.exit(1)

# Constants
SESSION_FILE = "session.json"


def get_password():
    """Get password input with fallback for terminals without getpass"""
    try:
        import getpass
        return getpass.getpass("Instagram password (hidden): ")
    except Exception:
        print("Note: Password will be visible")
        return input("Instagram password: ")


def extract_message_info(item: dict, my_user_id: Optional[str] = None) -> dict:
    """
    Extract readable details, category, and text/media representation from a raw thread item.
    Categorizes messages into 'text', 'media' (photos/videos), 'link', 'share', or 'other'.
    """
    msg_id = (
        item.get('item_id') or 
        item.get('id') or 
        item.get('client_context') or 
        'Unknown'
    )
    user_id = str(item.get('user_id', 'Unknown'))
    item_type = item.get('item_type', 'text')
    
    # Check if sent by the viewer / logged-in user
    is_sent_by_viewer = item.get('is_sent_by_viewer')
    if is_sent_by_viewer is None and my_user_id:
        is_sent_by_viewer = (str(user_id) == str(my_user_id))
    
    # Timestamp formatting
    timestamp_str = ""
    if 'timestamp' in item:
        try:
            ts = int(item['timestamp'])
            # Instagram timestamps are typically in microseconds (16 digits)
            if ts > 1e11:
                ts = ts / 1000000
            timestamp_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp_str = str(item['timestamp'])
            
    # Determine category & summary representation
    category = "text"
    summary = ""
    
    raw_text = item.get('text')
    if raw_text:
        summary = raw_text
        category = "text"
        
    link_obj = item.get('link')
    if link_obj:
        category = "link"
        url = ""
        if isinstance(link_obj, dict):
            url = link_obj.get('text') or link_obj.get('link_context', {}).get('link_url') or ""
        elif isinstance(link_obj, str):
            url = link_obj
        if not url and raw_text:
            url = raw_text
        summary = f"[Link] {url}" if url else "[Link]"
        
    if item_type in ('media', 'raven_media', 'visual_media') or item.get('media') or item.get('visual_media'):
        category = "media"
        media_obj = item.get('media', {})
        if isinstance(media_obj, dict) and media_obj.get('media_type') == 2:
            summary = "[Video]"
        elif item_type in ('raven_media', 'visual_media') or item.get('visual_media'):
            summary = "[Disappearing Photo/Video]"
        else:
            summary = "[Photo]"
            
    elif item_type in ('media_share', 'reel_share', 'story_share', 'clip') or item.get('media_share') or item.get('reel_share'):
        category = "share"
        summary = f"[Shared {item_type.replace('_', ' ').title()}]"
        
    elif item_type == 'animated_media' or item.get('animated_media'):
        category = "media"
        summary = "[GIF / Animated Sticker]"
        
    elif item_type == 'voice_media' or item.get('voice_media'):
        category = "media"
        summary = "[Voice Note]"
        
    elif item_type.startswith('xma_') or item.get('xma_share'):
        category = "link"
        summary = "[Shared Link/Card]"
        
    elif not summary:
        summary = f"[{item_type}]"
        
    return {
        "id": str(msg_id),
        "user_id": user_id,
        "is_sent_by_viewer": bool(is_sent_by_viewer),
        "timestamp": timestamp_str,
        "item_type": item_type,
        "category": category,
        "summary": summary,
        "raw": item
    }


def load_session(client: Client, session_file: str) -> bool:
    """Load session with app version override to prevent out-of-date error"""
    if not os.path.exists(session_file):
        return False
    try:
        # override_app_version=True ensures outdated app profiles are refreshed
        # to the latest supported version
        try:
            client.load_settings(session_file, override_app_version=True)
        except TypeError:
            client.load_settings(session_file)
            
        # Test session validity
        try:
            client.account_info()
            return True
        except Exception:
            if client.user_id:
                return True
            return False
    except Exception:
        try:
            os.remove(session_file)
        except Exception:
            pass
        return False


def save_session(client: Client, session_file: str) -> bool:
    """Save session to file"""
    try:
        client.dump_settings(session_file)
        return True
    except Exception:
        return False


class IGDMTool:
    def __init__(self):
        self.client = Client()
        self.logged_in = False
        self.selected_thread_id = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches: List[dict] = []
        self.last_filter_desc: str = ""
        print("[+] IGDMTool initialized")
        
        # Check for existing session automatically
        self._check_existing_session()

    def _check_existing_session(self):
        """Silently check if a valid session exists on startup"""
        if os.path.exists(SESSION_FILE):
            if load_session(self.client, SESSION_FILE):
                try:
                    user_info = self.client.account_info()
                    self.my_username = user_info.username
                    self.my_user_id = str(user_info.pk)
                    self.logged_in = True
                    print(f"[+] Automatically restored session for: {self.my_username}")
                except Exception:
                    if self.client.user_id:
                        self.my_user_id = str(self.client.user_id)
                        self.my_username = self.client.username or self.my_user_id
                        self.logged_in = True
                        print(f"[+] Automatically restored session for: {self.my_username}")

    def login(self):
        """Login menu supporting Username/Password, 2FA, and Session ID Cookie"""
        print("\n=== LOGIN / ACCOUNT ===")
        
        if self.logged_in:
            print(f"Currently logged in as: {self.my_username} (ID: {self.my_user_id})")
            print("1. Continue with current session")
            print("2. Switch account / Log in again")
            print("3. Log out and clear saved session")
            choice = input("\nSelect option (1-3): ").strip()
            if choice == "1":
                return True
            elif choice == "3":
                self.logout()
                return False
            # choice == "2" proceeds to fresh login below
        
        print("\nSelect Login Method:")
        print("1. Username & Password (Standard - with 2FA support)")
        print("2. Session ID Cookie (RECOMMENDED - bypasses 'Instagram app out of date', checkpoints & 2FA)")
        print("3. Back to main menu")
        
        method = input("\nSelect option (1-3): ").strip()
        if method == "1":
            return self.login_credentials()
        elif method == "2":
            return self.login_sessionid()
        else:
            return False

    def login_credentials(self):
        """Standard username and password login with 2FA handling and out-of-date troubleshooting"""
        print("\n--- USERNAME & PASSWORD LOGIN ---")
        username = input("Instagram username: ").strip()
        if not username:
            return False
        
        password = get_password().strip()
        if not password:
            return False
        
        try:
            print("Logging in to Instagram...")
            self.client.login(username, password)
            
            try:
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)
            except Exception:
                self.my_user_id = str(self.client.user_id)
                self.my_username = self.client.username or username
                
            save_session(self.client, SESSION_FILE)
            print(f"[+] Logged in as: {self.my_username}")
            self.logged_in = True
            return True

        except TwoFactorRequired:
            print("\n[!] Two-Factor Authentication (2FA) is enabled on this account.")
            code = input("Enter your 6-digit verification code (from SMS or Authenticator App): ").strip()
            if not code:
                print("2FA code cannot be empty.")
                return False
            try:
                print("Submitting 2FA verification code...")
                self.client.login(username, password, verification_code=code)
                try:
                    user_info = self.client.account_info()
                    self.my_username = user_info.username
                    self.my_user_id = str(user_info.pk)
                except Exception:
                    self.my_user_id = str(self.client.user_id)
                    self.my_username = self.client.username or username
                save_session(self.client, SESSION_FILE)
                print(f"[+] Logged in as: {self.my_username}")
                self.logged_in = True
                return True
            except Exception as e2fa:
                print(f"2FA login failed: {e2fa}")
                return False

        except (ClientNeedsUpgradeError, Exception) as e:
            err_str = str(e).lower()
            if "out of date" in err_str or "needs_upgrade" in err_str or "upgrade" in err_str:
                print("\n" + "=" * 65)
                print("[!] INSTAGRAM 'APP OUT OF DATE' ERROR DETECTED")
                print("=" * 65)
                print("Instagram is blocking mobile login from this client/IP:")
                print(f"  Error: {e}")
                print("\nWhy this happens:")
                print("Instagram flags mobile app login attempts from scripts or accounts that")
                print("were recently compromised/hacked and requires a modern client signature.")
                print("\nSOLUTION (Works 100%):")
                print("Use Method 2: 'Session ID Cookie Login'!")
                print("1. Open https://www.instagram.com in your web browser (Chrome/Edge/Firefox).")
                print("2. Make sure you are logged in there.")
                print("3. Press F12 -> Application -> Cookies -> https://www.instagram.com")
                print("4. Copy the value of the 'sessionid' cookie.")
                print("5. Paste it into this tool to bypass all mobile app version checks!")
                print("=" * 65 + "\n")
                
                switch = input("Would you like to log in with your browser Session ID now? (y/n): ").strip().lower()
                if switch == 'y':
                    return self.login_sessionid()
                return False
            
            elif "challenge" in err_str or "checkpoint" in err_str:
                print(f"\n[!] Instagram checkpoint/challenge required: {e}")
                print("Instagram detected unusual activity (common when accounts are recently hacked).")
                print("You can bypass this by logging in on your web browser and using Session ID Login.")
                switch = input("Would you like to log in with your browser Session ID now? (y/n): ").strip().lower()
                if switch == 'y':
                    return self.login_sessionid()
                return False
            else:
                print(f"Login failed: {e}")
                return False

    def login_sessionid(self):
        """Login using Instagram Web sessionid cookie (bypasses app out-of-date and 2FA issues)"""
        print("\n" + "=" * 60)
        print("LOGIN WITH INSTAGRAM BROWSER SESSION ID")
        print("=" * 60)
        print("This method connects directly using your browser's authenticated session.")
        print("It completely bypasses 'Instagram app out of date', 2FA, and checkpoint blocks!\n")
        print("How to get your sessionid in 3 easy steps:")
        print("1. Open https://www.instagram.com in your browser (Chrome, Edge, Firefox, Brave, Safari)")
        print("   and log in to your account.")
        print("2. Open Developer Tools:")
        print("   - Chrome/Edge/Brave: Press F12 (or right-click anywhere -> Inspect)")
        print("     Go to: 'Application' tab -> 'Cookies' -> 'https://www.instagram.com'")
        print("   - Firefox: Press F12 -> 'Storage' tab -> 'Cookies' -> 'https://www.instagram.com'")
        print("   - Safari: Preferences -> Advanced -> Show Develop menu -> Inspect -> Storage -> Cookies")
        print("3. Find the cookie named 'sessionid', double-click its Value, and copy it.")
        print("   (It is a long string, often starting with your user ID numbers)")
        print("=" * 60)
        
        sessionid = input("\nPaste your sessionid here (or press Enter to cancel): ").strip()
        if not sessionid:
            print("Session ID login cancelled.")
            return False
        
        # Clean quotes if user pasted with quotation marks
        sessionid = sessionid.strip('"\'')
        
        try:
            print("Authenticating session with Instagram...")
            self.client.login_by_sessionid(sessionid)
            
            try:
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)
            except Exception:
                if self.client.user_id:
                    self.my_user_id = str(self.client.user_id)
                self.my_username = self.client.username or (f"User_{self.my_user_id}" if self.my_user_id else "User")
            
            save_session(self.client, SESSION_FILE)
            print(f"[+] Successfully authenticated as: {self.my_username} (User ID: {self.my_user_id})")
            self.logged_in = True
            return True
        except Exception as e:
            print(f"\nSession ID login failed: {e}")
            print("Tips:")
            print("- Ensure you copied the FULL sessionid value without extra spaces.")
            print("- Make sure you are actively logged in to Instagram in that browser.")
            print("- If your session expired, refresh instagram.com in browser and copy the new sessionid.")
            return False

    def logout(self):
        """Log out and remove stored session file"""
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except Exception:
                pass
        self.client = Client()
        self.logged_in = False
        self.selected_thread_id = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches = []
        self.last_filter_desc = ""
        print("[+] Logged out successfully and cleared local session.")

    def list_threads_raw_api(self):
        """Use raw API call to get inbox threads with rich message previews"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return False
        
        print("\n=== MESSAGE THREADS ===")
        
        try:
            print("Fetching threads from inbox...")
            response = self.client.private_request("direct_v2/inbox/", params={
                "visual_message_return_type": "unseen",
                "thread_message_limit": "10",
                "persistentBadging": "true",
                "limit": "20"
            })
            
            if not response or 'inbox' not in response:
                print("No inbox data received")
                return False
            
            inbox = response['inbox']
            threads = inbox.get('threads', [])
            
            if not threads:
                print("No conversations found in inbox")
                return False
            
            print(f"Found {len(threads)} recent conversations:\n")
            
            for i, thread in enumerate(threads, 1):
                try:
                    thread_id = thread.get('thread_id', 'Unknown')
                    thread_title = thread.get('thread_title')
                    
                    # Get usernames
                    users = thread.get('users', [])
                    usernames = [u.get('username', '') for u in users if u.get('username')]
                    
                    if thread_title:
                        title_str = f"{thread_title} ({', '.join(usernames[:3])})"
                    elif usernames:
                        title_str = ", ".join(usernames[:3])
                        if len(usernames) > 3:
                            title_str += f" and {len(usernames)-3} others"
                    else:
                        title_str = "Unknown thread"
                    
                    # Get last message preview using extractor
                    items = thread.get('items', [])
                    last_msg = ""
                    if items:
                        info = extract_message_info(items[0], self.my_user_id)
                        last_msg = info['summary'][:60]
                        if len(info['summary']) > 60:
                            last_msg += "..."
                    else:
                        last_msg = "[No messages]"
                    
                    print(f"{i:2d}. Conversation: {title_str}")
                    print(f"    Thread ID: {thread_id}")
                    print(f"    Latest: {last_msg}")
                    print()
                    
                except Exception as e:
                    print(f"{i:2d}. [Error displaying thread: {e}]")
                    continue
            
            # User selection
            try:
                choice = input("Select conversation number (or Enter to cancel): ").strip()
                if choice:
                    idx = int(choice) - 1
                    if 0 <= idx < len(threads):
                        self.selected_thread_id = str(threads[idx].get('thread_id'))
                        print(f"[+] Selected thread: {self.selected_thread_id}")
                        return True
                    else:
                        print("Invalid selection number")
            except Exception:
                print("Invalid input")
            
            return False
            
        except Exception as e:
            print(f"Failed to list threads: {e}")
            return False

    def select_thread(self):
        """Select thread by direct thread ID or Instagram username"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return False
        
        print("\n=== SELECT THREAD ===")
        thread_input = input("Enter thread ID or Instagram username: ").strip()
        if not thread_input:
            return False
        
        try:
            if thread_input.isdigit() and len(thread_input) > 8:
                self.selected_thread_id = thread_input
                print(f"[+] Selected thread ID: {thread_input}")
                return True
            else:
                print(f"Looking up username: {thread_input}")
                user_id = self.client.user_id_from_username(thread_input)
                print(f"Found user ID: {user_id}")
                
                # Search inbox for matching thread
                print("Locating conversation in inbox...")
                response = self.client.private_request("direct_v2/inbox/", params={
                    "visual_message_return_type": "unseen",
                    "thread_message_limit": "10",
                    "persistentBadging": "true",
                    "limit": "50"
                })
                
                if response and 'inbox' in response:
                    threads = response['inbox'].get('threads', [])
                    for thread in threads:
                        users = thread.get('users', [])
                        for user in users:
                            if str(user.get('pk', '')) == str(user_id):
                                self.selected_thread_id = str(thread.get('thread_id'))
                                print(f"[+] Found conversation thread: {self.selected_thread_id}")
                                return True
                
                print(f"No existing conversation found in recent inbox for @{thread_input}.")
                print("Tip: If you know the thread ID, enter it directly, or choose from Option 2.")
                return False
        except Exception as e:
            print(f"Failed to select thread: {e}")
            return False

    def fetch_all_messages_paginated(self, max_messages: int = 5000) -> List[dict]:
        """Fetch messages with PROPER Instagram pagination using cursors"""
        all_messages = []
        cursor = None
        page = 1
        consecutive_empty_pages = 0
        
        print(f"Fetching up to {max_messages} messages with cursor pagination...")
        
        while len(all_messages) < max_messages and consecutive_empty_pages < 3:
            try:
                print(f"Fetching page {page}... (retrieved {len(all_messages)} messages so far)")
                
                params = {
                    "visual_message_return_type": "unseen",
                    "direction": "older",
                    "limit": "75"  # Instagram's max limit per request
                }
                
                if cursor:
                    params["cursor"] = cursor
                
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}/", 
                    params=params
                )
                
                if not response or 'thread' not in response:
                    print(f"No response data on page {page}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:
                        break
                    page += 1
                    time.sleep(1)
                    continue
                
                thread = response['thread']
                items = thread.get('items', [])
                
                if not items:
                    print(f"No items on page {page}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:
                        print("Reached beginning of conversation.")
                        break
                    page += 1
                    time.sleep(1)
                    continue
                
                consecutive_empty_pages = 0
                
                new_messages = 0
                for item in items:
                    if len(all_messages) >= max_messages:
                        break
                    all_messages.append(item)
                    new_messages += 1
                
                print(f"Page {page}: Got {new_messages} messages")
                
                # Extract cursor for next older page
                cursor = None
                if 'oldest_cursor' in thread and thread['oldest_cursor']:
                    cursor = thread['oldest_cursor']
                elif 'next_cursor' in thread and thread['next_cursor']:
                    cursor = thread['next_cursor']
                elif items and 'timestamp' in items[-1]:
                    cursor = str(items[-1]['timestamp'])
                elif 'paging_info' in response and 'max_id' in response['paging_info']:
                    cursor = response['paging_info']['max_id']
                elif items:
                    last_item = items[-1]
                    cursor = (last_item.get('item_id') or 
                             last_item.get('id') or 
                             last_item.get('client_context'))
                
                if not cursor:
                    print("No cursor found - reached the earliest message.")
                    break
                
                page += 1
                time.sleep(0.6)  # Safe delay to prevent rate limits
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:
                    break
                page += 1
                time.sleep(2)
        
        print(f"Total messages retrieved: {len(all_messages)} across {page-1} pages\n")
        return all_messages

    def view_messages_raw_api(self):
        """View messages with structured previews for text, photos, and links"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        if not self.selected_thread_id:
            print("Please select a conversation thread first (Option 2 or 3)")
            return
        
        print(f"\n=== VIEW MESSAGES (THREAD {self.selected_thread_id}) ===")
        
        try:
            amount_str = input("Number of messages to view (default 20): ").strip()
            amount = int(amount_str) if amount_str.isdigit() else 20
            
            if amount > 75:
                items = self.fetch_all_messages_paginated(amount)
            else:
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}/", 
                    params={
                        "visual_message_return_type": "unseen",
                        "direction": "older",
                        "limit": str(amount)
                    }
                )
                if not response or 'thread' not in response:
                    print("No thread data received")
                    return
                items = response['thread'].get('items', [])
            
            if not items:
                print("No messages found in this thread.")
                return
            
            print(f"\nFound {len(items)} messages (newest first):")
            print("-" * 75)
            
            for item in items[:25]:
                try:
                    info = extract_message_info(item, self.my_user_id)
                    
                    sender = f"ID: {info['user_id']}"
                    if info['is_sent_by_viewer'] or info['user_id'] == str(self.my_user_id):
                        sender = f"{self.my_username} (YOU)"
                    
                    print(f"ID:       {info['id']}")
                    print(f"From:     {sender}")
                    print(f"Time:     {info['timestamp']}")
                    print(f"Type:     {info['category'].upper()} ({info['item_type']})")
                    print(f"Content:  {info['summary']}")
                    print("-" * 40)
                    
                except Exception as e:
                    print(f"Error displaying message: {e}")
                    continue
                    
        except Exception as e:
            print(f"Failed to view messages: {e}")

    def search_messages_raw_api(self):
        """
        Search and filter messages to unsend.
        Supports:
        - ALL messages sent by user (essential for recovering from hacked accounts)
        - Keywords in text or link URLs
        - Photos & Videos only
        - Links / URLs only
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        if not self.selected_thread_id:
            print("Please select a conversation thread first (Option 2 or 3)")
            return
        
        print("\n=== SEARCH / FILTER MESSAGES TO UNSEND ===")
        print("Select what you want to find & unsend:")
        print("1. ALL messages sent by you (Recommended for hacked accounts - unsend everything!)")
        print("2. Search by keyword(s) (e.g. 'scam', 'crypto', 'gift', 'free', etc.)")
        print("3. Only Photos & Videos (photos, disappearing snaps, videos, media)")
        print("4. Only Links & URLs (scam links, web addresses)")
        print("5. Cancel")
        
        filter_mode = input("\nSelect filter option (1-5): ").strip()
        if filter_mode not in ("1", "2", "3", "4"):
            print("Cancelled.")
            return
        
        keywords = []
        filter_desc = ""
        
        if filter_mode == "1":
            filter_desc = "ALL messages sent by your account"
        elif filter_mode == "2":
            kw_input = input("Enter keywords (comma-separated, e.g. 'gift,link,crypto'): ").strip()
            if not kw_input:
                print("No keywords entered.")
                return
            keywords = [k.strip().lower() for k in kw_input.split(",") if k.strip()]
            filter_desc = f"Messages containing keywords: {', '.join(keywords)}"
        elif filter_mode == "3":
            filter_desc = "Photos & Videos (all media)"
        elif filter_mode == "4":
            filter_desc = "Links & URLs"
        
        try:
            amount_str = input("Max messages to scan in thread history (default 1000): ").strip()
            amount = int(amount_str) if amount_str.isdigit() else 1000
            
            print(f"\nFiltering for: {filter_desc}")
            print(f"Scanning up to {amount} messages...")
            
            if amount > 75:
                items = self.fetch_all_messages_paginated(amount)
            else:
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}/", 
                    params={
                        "visual_message_return_type": "unseen",
                        "direction": "older",
                        "limit": str(amount)
                    }
                )
                if not response or 'thread' not in response:
                    print("No thread data received")
                    return
                items = response['thread'].get('items', [])
            
            if not items:
                print("No messages found in thread.")
                return
            
            matched_items = []
            
            for i, raw_item in enumerate(items, 1):
                try:
                    info = extract_message_info(raw_item, self.my_user_id)
                    is_mine = info['is_sent_by_viewer'] or (info['user_id'] == str(self.my_user_id))
                    
                    matched = False
                    
                    if filter_mode == "1":
                        # Match all messages sent by this account
                        if is_mine:
                            matched = True
                            
                    elif filter_mode == "2":
                        # Match keywords in text or summary
                        text_lower = info['summary'].lower()
                        if any(kw in text_lower for kw in keywords):
                            matched = True
                            
                    elif filter_mode == "3":
                        # Photos & Media only
                        if info['category'] == 'media':
                            matched = True
                            
                    elif filter_mode == "4":
                        # Links only
                        if info['category'] == 'link' or 'http://' in info['summary'] or 'https://' in info['summary']:
                            matched = True
                    
                    if matched:
                        matched_items.append(info)
                        
                        sender_label = f"{self.my_username} (YOU)" if is_mine else f"Other User ({info['user_id']})"
                        disp_summary = info['summary'][:80] + "..." if len(info['summary']) > 80 else info['summary']
                        
                        print(f"  [Match #{len(matched_items)}] ID: {info['id']} | Type: {info['category'].upper()} | From: {sender_label}")
                        print(f"    Content: {disp_summary}")
                        
                except Exception as e:
                    continue
            
            print("\n" + "=" * 50)
            print(f"SCAN COMPLETE: Found {len(matched_items)} matching messages.")
            print("=" * 50)
            
            self.last_matches = matched_items
            self.last_filter_desc = filter_desc
            
            own_count = sum(1 for m in matched_items if m['is_sent_by_viewer'] or m['user_id'] == str(self.my_user_id))
            print(f"Messages from YOUR account ready to unsend: {own_count}")
            if len(matched_items) - own_count > 0:
                print(f"Messages from other participants (will NOT be unsent): {len(matched_items) - own_count}")
            
            if own_count > 0:
                print("\nReady! Select Option 6 from the main menu to unsend these messages.")
            else:
                print("\nNo messages from your account matched the filter.")
                
        except Exception as e:
            print(f"Search failed: {e}")

    def delete_messages_raw_api(self):
        """UNSEND messages using proper Instagram unsend API endpoints (handles texts, photos, and links)"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        if not self.selected_thread_id:
            print("Please select a thread first (Option 2 or 3)")
            return
        
        print("\n=== BULK UNSEND MESSAGES ===")
        
        if not self.last_matches:
            print("No matching messages selected yet.")
            print("Please run Option 5 (Search / Filter Messages) first!")
            return
        
        matches = self.last_matches
        
        # Separate own messages vs other participants' messages
        own_messages = [
            m for m in matches 
            if m['is_sent_by_viewer'] or (m['user_id'] == str(self.my_user_id))
        ]
        other_messages = [
            m for m in matches 
            if not (m['is_sent_by_viewer'] or (m['user_id'] == str(self.my_user_id)))
        ]
        
        print(f"Filter used: {self.last_filter_desc}")
        print(f"Total matched messages: {len(matches)}")
        print(f"Messages you can unsend: {len(own_messages)}")
        print(f"Other participants' messages: {len(other_messages)} (Instagram only allows unsending your own messages)")
        
        if len(own_messages) == 0:
            print("\nNo messages from your account to unsend.")
            return
        
        # Breakdown by category
        text_count = sum(1 for m in own_messages if m['category'] == 'text')
        media_count = sum(1 for m in own_messages if m['category'] == 'media')
        link_count = sum(1 for m in own_messages if m['category'] == 'link')
        other_count = len(own_messages) - (text_count + media_count + link_count)
        
        print(f"\nBreakdown to unsend:")
        print(f"  - Texts:          {text_count}")
        print(f"  - Photos & Media: {media_count}")
        print(f"  - Links:          {link_count}")
        if other_count > 0:
            print(f"  - Other/Shared:   {other_count}")
            
        print(f"\nPreview of first 10 messages that will be UNSENT:")
        print("-" * 65)
        for i, m in enumerate(own_messages[:10], 1):
            summary = m['summary'][:55] + "..." if len(m['summary']) > 55 else m['summary']
            print(f"{i:2d}. [{m['category'].upper()}] ID: {m['id']} | Time: {m['timestamp']}")
            print(f"    Content: {summary}")
            
        if len(own_messages) > 10:
            print(f"... and {len(own_messages) - 10} more messages")
        print("-" * 65)
        
        confirm = input(f"\nType 'YES' (in capital letters) to permanently UNSEND {len(own_messages)} messages: ").strip()
        if confirm != 'YES':
            print("Unsend cancelled by user.")
            return
        
        print(f"\nStarting unsend process for {len(own_messages)} messages...")
        print("Note: Adding a 1-second delay between deletions to protect your account from rate limits.\n")
        
        deleted = 0
        failed = 0
        
        for i, m in enumerate(own_messages, 1):
            msg_id = m['id']
            if not msg_id or msg_id == 'Unknown':
                print(f"[{i}/{len(own_messages)}] SKIP: Invalid message ID")
                failed += 1
                continue
            
            print(f"[{i}/{len(own_messages)}] Unsending {m['category'].upper()} ({msg_id})...", end=" ")
            
            success = False
            
            # Method 1: Instagram standard direct message delete/unsend endpoint
            try:
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}/items/{msg_id}/delete/",
                    data={
                        "_uuid": self.client.uuid,
                        "_uid": self.my_user_id,
                        "_csrftoken": self.client.token
                    },
                    with_signature=False
                )
                if response and response.get('status') == 'ok':
                    success = True
            except Exception:
                pass
            
            # Method 2: Fallback to built-in direct_message_delete
            if not success and msg_id.isdigit() and str(self.selected_thread_id).isdigit():
                try:
                    success = self.client.direct_message_delete(int(self.selected_thread_id), int(msg_id))
                except Exception:
                    pass
            
            # Method 3: Fallback to broadcast item_unsend endpoint
            if not success:
                try:
                    response2 = self.client.private_request(
                        "direct_v2/threads/broadcast/item_unsend/",
                        data={
                            "thread_id": self.selected_thread_id,
                            "item_id": msg_id,
                            "_uuid": self.client.uuid,
                            "_uid": self.my_user_id,
                            "_csrftoken": self.client.token
                        },
                        with_signature=False
                    )
                    if response2 and response2.get('status') == 'ok':
                        success = True
                except Exception:
                    pass
            
            if success:
                print("[+] Unsent")
                deleted += 1
            else:
                print("[-] Failed")
                failed += 1
                
            time.sleep(1.0)
            
        print("\n" + "=" * 50)
        print("UNSEND PROCESS COMPLETE")
        print(f"Successfully unsent: {deleted} messages")
        print(f"Failed:              {failed} messages")
        print("=" * 50)
        
        # Clear cached matches
        self.last_matches = []
        self.last_filter_desc = ""

    def menu_loop(self):
        """Main menu loop"""
        while True:
            try:
                print("\n" + "=" * 55)
                print("   INSTAGRAM DM TOOL - UNLIMITED PAGINATION & UNSEND")
                print("=" * 55)
                
                if self.logged_in:
                    print(f"Status:   LOGGED IN as @{self.my_username} (ID: {self.my_user_id})")
                else:
                    print("Status:   NOT LOGGED IN (Select Option 1 to connect)")
                
                if self.selected_thread_id:
                    print(f"Thread:   Selected ID: {self.selected_thread_id}")
                else:
                    print("Thread:   None selected (Select Option 2 or 3)")
                    
                if self.last_matches:
                    print(f"Filter:   {len(self.last_matches)} messages queued ({self.last_filter_desc})")
                
                print("\nOptions:")
                print("1. Login / Account (Username/Password or Session ID Cookie)")
                print("2. List Conversations (Raw API)")
                print("3. Select Conversation (by Username or Thread ID)")
                print("4. View Messages (Unlimited pagination)")
                print("5. Search / Filter Messages (All, Keywords, Photos, Links)")
                print("6. Unsend Queued Messages (Working)")
                print("7. Logout / Switch Account")
                print("8. Exit")
                
                choice = input("\nSelect option (1-8): ").strip()
                
                if choice == "1":
                    self.login()
                elif choice == "2":
                    self.list_threads_raw_api()
                elif choice == "3":
                    self.select_thread()
                elif choice == "4":
                    self.view_messages_raw_api()
                elif choice == "5":
                    self.search_messages_raw_api()
                elif choice == "6":
                    self.delete_messages_raw_api()
                elif choice == "7":
                    self.logout()
                elif choice == "8":
                    print("Exiting. Goodbye!")
                    break
                else:
                    print("Invalid option. Please enter 1-8.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting. Goodbye!")
                break
            except Exception as e:
                print(f"\nUnexpected error in menu: {e}")


def main():
    try:
        print("Instagram DM Tool - UNLIMITED PAGINATION + WORKING BULK UNSEND")
        print("[+] Proper cursor-based pagination")
        print("[+] Bulk unsend text, links, photos & media")
        print("[+] Support for 2FA and Session ID login (bypasses out-of-date error)")
        tool = IGDMTool()
        tool.menu_loop()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
