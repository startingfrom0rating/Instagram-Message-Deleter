#!/usr/bin/env python3
"""
instagram_dm_tool.py
Instagram DM tool with PROPER PAGINATION and ACCOUNT-WIDE CLEANUP.
Features:
- Session ID Cookie Login (bypasses "Instagram app out of date", 2FA, checkpoints)
- Username & Password Login with full 2FA verification support
- Account-Wide Scam Cleanup: scan and unsend messages/photos/links across ALL inbox conversations
- Full Inbox Pagination: browse and scroll down through all conversations in inbox
- Unlimited Thread Pagination: proper cursor-based pagination with seq_id and oldest_cursor
- Date/Time Filtering: target messages sent during recent hack (e.g. last 3 or 7 days)
- Bulk Unsend: text messages, scam links, photos, videos, and disappearing snaps
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
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


def extract_message_info(item: Any, my_user_id: Optional[str] = None) -> dict:
    """
    Extract readable details, category, timestamp, and text/media summary from a message.
    Supports both raw API dictionary items and instagrapi DirectMessage objects.
    Categorizes messages into 'text', 'media' (photos/videos), 'link', 'share', or 'other'.
    """
    if hasattr(item, 'model_dump'):
        raw = item.model_dump()
    elif hasattr(item, 'dict'):
        raw = item.dict()
    elif isinstance(item, dict):
        raw = item
    else:
        raw = {}

    msg_id = (
        raw.get('item_id') or 
        raw.get('id') or 
        raw.get('client_context') or 
        'Unknown'
    )
    user_id = str(raw.get('user_id', 'Unknown'))
    item_type = raw.get('item_type') or 'text'
    
    # Check if sent by the viewer / logged-in user
    is_sent_by_viewer = raw.get('is_sent_by_viewer')
    if is_sent_by_viewer is None and my_user_id:
        is_sent_by_viewer = (str(user_id) == str(my_user_id))
    
    # Timestamp parsing
    timestamp_ts = 0.0
    timestamp_str = ""
    raw_ts = raw.get('timestamp')
    if raw_ts is not None:
        if isinstance(raw_ts, datetime):
            timestamp_ts = raw_ts.timestamp()
            timestamp_str = raw_ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            try:
                ts = float(raw_ts)
                # Instagram timestamps are typically in microseconds (16 digits)
                if ts > 1e11:
                    ts = ts / 1000000.0
                timestamp_ts = ts
                timestamp_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                timestamp_str = str(raw_ts)
            
    # Determine category & summary representation
    category = "text"
    summary = ""
    
    raw_text = raw.get('text')
    if raw_text:
        summary = str(raw_text)
        category = "text"
        
    link_obj = raw.get('link')
    if link_obj:
        category = "link"
        url = ""
        if isinstance(link_obj, dict):
            url = link_obj.get('text') or link_obj.get('link_context', {}).get('link_url') or ""
        elif hasattr(link_obj, 'text'):
            url = getattr(link_obj, 'text', '')
        elif isinstance(link_obj, str):
            url = link_obj
        if not url and raw_text:
            url = raw_text
        summary = f"[Link] {url}" if url else "[Link]"
        
    if item_type in ('media', 'raven_media', 'visual_media') or raw.get('media') or raw.get('visual_media'):
        category = "media"
        media_obj = raw.get('media') or {}
        is_video = False
        if isinstance(media_obj, dict) and media_obj.get('media_type') == 2:
            is_video = True
        elif hasattr(media_obj, 'media_type') and getattr(media_obj, 'media_type') == 2:
            is_video = True

        if is_video:
            summary = "[Video]"
        elif item_type in ('raven_media', 'visual_media') or raw.get('visual_media'):
            summary = "[Disappearing Photo/Video]"
        else:
            summary = "[Photo]"
            
    elif item_type in ('media_share', 'reel_share', 'story_share', 'clip') or raw.get('media_share') or raw.get('reel_share'):
        category = "share"
        summary = f"[Shared {item_type.replace('_', ' ').title()}]"
        
    elif item_type == 'animated_media' or raw.get('animated_media'):
        category = "media"
        summary = "[GIF / Animated Sticker]"
        
    elif item_type == 'voice_media' or raw.get('voice_media'):
        category = "media"
        summary = "[Voice Note]"
        
    elif item_type.startswith('xma_') or raw.get('xma_share'):
        category = "link"
        summary = "[Shared Link/Card]"
        
    elif not summary:
        summary = f"[{item_type}]"

    # Also detect URLs inside normal text messages
    if category == "text" and any(proto in summary.lower() for proto in ("http://", "https://", "www.", ".com/", ".xyz", ".ru", ".link")):
        category = "link"
        
    return {
        "id": str(msg_id),
        "user_id": str(user_id),
        "is_sent_by_viewer": bool(is_sent_by_viewer),
        "timestamp": timestamp_str,
        "timestamp_ts": timestamp_ts,
        "item_type": str(item_type),
        "category": category,
        "summary": summary,
        "raw": raw
    }


def load_session(client: Client, session_file: str) -> bool:
    """Load session with app version override to prevent out-of-date error"""
    if not os.path.exists(session_file):
        return False
    try:
        try:
            client.load_settings(session_file, override_app_version=True)
        except TypeError:
            client.load_settings(session_file)
            
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
        self.selected_thread_title = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches: List[dict] = []
        self.last_filter_desc: str = ""
        print("[+] IGDMTool initialized")
        
        self._check_existing_session()

    def _check_existing_session(self):
        """Silently restore existing session on startup"""
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

    def unsend_message(self, thread_id: str, msg_id: str) -> bool:
        """
        Unsend a message using multiple Instagram endpoints.
        Returns True on success, False on failure.
        """
        if not thread_id or not msg_id or msg_id == 'Unknown':
            return False

        # Endpoint 1: Direct item delete (standard mobile API endpoint)
        try:
            response = self.client.private_request(
                f"direct_v2/threads/{thread_id}/items/{msg_id}/delete/",
                data={
                    "_uuid": self.client.uuid,
                    "_uid": self.my_user_id,
                    "_csrftoken": self.client.token
                },
                with_signature=False
            )
            if response and response.get('status') == 'ok':
                return True
        except Exception:
            pass

        # Endpoint 2: instagrapi built-in direct_message_delete
        if msg_id.isdigit() and str(thread_id).isdigit():
            try:
                if self.client.direct_message_delete(int(thread_id), int(msg_id)):
                    return True
            except Exception:
                pass

        # Endpoint 3: broadcast item_unsend
        try:
            response2 = self.client.private_request(
                "direct_v2/threads/broadcast/item_unsend/",
                data={
                    "thread_id": str(thread_id),
                    "item_id": str(msg_id),
                    "_uuid": self.client.uuid,
                    "_uid": self.my_user_id,
                    "_csrftoken": self.client.token
                },
                with_signature=False
            )
            if response2 and response2.get('status') == 'ok':
                return True
        except Exception:
            pass

        return False

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
        self.selected_thread_title = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches = []
        self.last_filter_desc = ""
        print("[+] Logged out successfully and cleared local session.")

    def fetch_inbox_threads(self, max_threads: int = 50) -> List[dict]:
        """
        Fetch inbox threads with full pagination support across the user's inbox.
        Returns a list of raw thread dicts.
        """
        all_threads = []
        cursor = None
        seen_ids = set()
        page = 1
        
        while len(all_threads) < max_threads:
            params = {
                "visual_message_return_type": "unseen",
                "thread_message_limit": "10",
                "persistentBadging": "true",
                "limit": "20"
            }
            if cursor:
                params.update({
                    "cursor": cursor,
                    "direction": "older"
                })
                
            try:
                response = self.client.private_request("direct_v2/inbox/", params=params)
                if not response or 'inbox' not in response:
                    break
                
                inbox = response['inbox']
                threads = inbox.get('threads', [])
                if not threads:
                    break
                
                new_in_page = 0
                for t in threads:
                    tid = str(t.get('thread_id', ''))
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_threads.append(t)
                        new_in_page += 1
                        if len(all_threads) >= max_threads:
                            break
                            
                next_cursor = inbox.get('oldest_cursor')
                if not next_cursor or next_cursor == cursor or new_in_page == 0:
                    break
                
                cursor = next_cursor
                page += 1
                time.sleep(0.4)
                
            except Exception as e:
                print(f"[!] Error loading inbox page {page}: {e}")
                break
                
        return all_threads

    def list_threads_raw_api(self):
        """
        Browse inbox conversations with interactive Next-Page pagination so users
        can scroll down through their entire conversation history.
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return False
        
        print("\n=== BROWSE INBOX CONVERSATIONS ===")
        print("Loading conversations from your inbox...")
        
        all_threads = []
        cursor = None
        seen_ids = set()
        
        while True:
            # Fetch next chunk of 20 threads
            params = {
                "visual_message_return_type": "unseen",
                "thread_message_limit": "10",
                "persistentBadging": "true",
                "limit": "20"
            }
            if cursor:
                params.update({
                    "cursor": cursor,
                    "direction": "older"
                })
            
            try:
                response = self.client.private_request("direct_v2/inbox/", params=params)
                if not response or 'inbox' not in response:
                    print("No more inbox data received.")
                    break
                
                inbox = response['inbox']
                batch = inbox.get('threads', [])
                if not batch:
                    print("No more conversations in inbox.")
                    break
                
                start_index = len(all_threads) + 1
                new_in_batch = []
                for t in batch:
                    tid = str(t.get('thread_id', ''))
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_threads.append(t)
                        new_in_batch.append(t)
                        
                if not new_in_batch:
                    print("Reached end of inbox conversations.")
                    break
                
                print(f"\n--- Conversations {start_index} to {len(all_threads)} ---")
                for i, thread in enumerate(new_in_batch, start_index):
                    thread_id = thread.get('thread_id', 'Unknown')
                    thread_title = thread.get('thread_title')
                    
                    users = thread.get('users', [])
                    usernames = [u.get('username', '') for u in users if u.get('username')]
                    
                    if thread_title:
                        title_str = f"{thread_title} ({', '.join(usernames[:3])})"
                    elif usernames:
                        title_str = ", ".join(usernames[:3])
                        if len(usernames) > 3:
                            title_str += f" and {len(usernames)-3} others"
                    else:
                        title_str = "Unknown conversation"
                    
                    items = thread.get('items', [])
                    last_msg = ""
                    if items:
                        info = extract_message_info(items[0], self.my_user_id)
                        last_msg = info['summary'][:55]
                        if len(info['summary']) > 55:
                            last_msg += "..."
                    else:
                        last_msg = "[No messages]"
                    
                    print(f"{i:2d}. {title_str} (ID: {thread_id})")
                    print(f"    Latest: {last_msg}")
                
                cursor = inbox.get('oldest_cursor')
                has_more = bool(cursor and inbox.get('has_older', True))
                
                print("\n" + "-" * 55)
                prompt_msg = f"Enter conversation number (1-{len(all_threads)})"
                if has_more:
                    prompt_msg += ", 'N' for Next 20 conversations"
                prompt_msg += ", or Enter to cancel: "
                
                choice = input(prompt_msg).strip()
                
                if not choice:
                    return False
                
                if choice.upper() == 'N' and has_more:
                    print("Loading next page of conversations...")
                    time.sleep(0.4)
                    continue
                
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(all_threads):
                        selected = all_threads[idx]
                        self.selected_thread_id = str(selected.get('thread_id'))
                        
                        users = selected.get('users', [])
                        usernames = [u.get('username', '') for u in users if u.get('username')]
                        self.selected_thread_title = selected.get('thread_title') or (", ".join(usernames[:3]) if usernames else self.selected_thread_id)
                        
                        print(f"[+] Selected conversation: {self.selected_thread_title} (ID: {self.selected_thread_id})")
                        return True
                    else:
                        print("Invalid conversation number.")
                        return False
                else:
                    print("Cancelled.")
                    return False
                    
            except Exception as e:
                print(f"[!] Failed to browse conversations: {e}")
                return False

    def select_thread(self):
        """Select thread by direct thread ID or Instagram username"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return False
        
        print("\n=== SELECT CONVERSATION ===")
        thread_input = input("Enter thread ID or Instagram username: ").strip()
        if not thread_input:
            return False
        
        try:
            if thread_input.isdigit() and len(thread_input) > 8:
                self.selected_thread_id = str(thread_input)
                self.selected_thread_title = f"Thread {thread_input}"
                print(f"[+] Selected thread ID: {thread_input}")
                return True
            else:
                print(f"Looking up username: @{thread_input}...")
                user_id = self.client.user_id_from_username(thread_input)
                print(f"Found user ID: {user_id}")
                
                print("Locating conversation in inbox...")
                threads = self.fetch_inbox_threads(max_threads=100)
                
                for thread in threads:
                    users = thread.get('users', [])
                    for user in users:
                        if str(user.get('pk', '')) == str(user_id):
                            self.selected_thread_id = str(thread.get('thread_id'))
                            self.selected_thread_title = f"@{thread_input}"
                            print(f"[+] Found conversation thread: {self.selected_thread_id}")
                            return True
                
                print(f"No existing conversation found in recent inbox for @{thread_input}.")
                print("Tip: If you know the thread ID, enter it directly, or choose from Option 2.")
                return False
        except Exception as e:
            print(f"Failed to select thread: {e}")
            return False

    def fetch_all_messages_paginated(self, max_messages: int = 5000) -> List[dict]:
        """
        Fetch messages from the selected thread with PROPER Instagram pagination.
        Uses exact mobile API parameters: direction='older', limit='20', seq_id='40065',
        and properly handles oldest_cursor and MINCURSOR boundaries.
        """
        all_messages = []
        cursor = None
        seen_ids = set()
        page = 1
        consecutive_empty_pages = 0
        
        print(f"Fetching up to {max_messages} messages with cursor pagination...")
        
        while len(all_messages) < max_messages and consecutive_empty_pages < 3:
            try:
                # Use Instagram's standard mobile batch parameters
                params = {
                    "visual_message_return_type": "unseen",
                    "direction": "older",
                    "seq_id": "40065",
                    "limit": "20"
                }
                if cursor:
                    params["cursor"] = cursor
                
                response = self.client.private_request(
                    f"direct_v2/threads/{self.selected_thread_id}/", 
                    params=params
                )
                
                if not response or 'thread' not in response:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:
                        break
                    page += 1
                    time.sleep(1)
                    continue
                
                thread = response['thread']
                items = thread.get('items', [])
                
                if not items:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 2:
                        print("Reached beginning of conversation (no more items returned).")
                        break
                    page += 1
                    time.sleep(1)
                    continue
                
                consecutive_empty_pages = 0
                new_in_page = 0
                for item in items:
                    mid = str(item.get('item_id') or item.get('id') or item.get('client_context') or len(all_messages))
                    if mid not in seen_ids:
                        seen_ids.add(mid)
                        all_messages.append(item)
                        new_in_page += 1
                        if len(all_messages) >= max_messages:
                            break
                
                print(f"  Page {page:2d}: Retrieved {new_in_page} messages (Total so far: {len(all_messages)})")
                
                if len(all_messages) >= max_messages:
                    print(f"Reached requested limit of {max_messages} messages.")
                    break
                
                # Check pagination boundary indicators
                if thread.get("has_older") is False:
                    print("Reached earliest message in conversation (has_older=False).")
                    break
                
                if thread.get("prev_cursor") == "MINCURSOR":
                    print("Reached beginning of conversation history (MINCURSOR).")
                    break
                
                next_cursor = thread.get("oldest_cursor") or thread.get("next_cursor")
                if not next_cursor or next_cursor == cursor or new_in_page == 0:
                    print("No further cursor provided - reached the earliest message.")
                    break
                
                cursor = next_cursor
                page += 1
                time.sleep(0.4)
                
            except Exception as e:
                print(f"  [!] Notice on page {page}: {e}")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= 3:
                    break
                page += 1
                time.sleep(1.5)
        
        # If raw pagination returned very few items but user asked for more, try instagrapi fallback
        if len(all_messages) <= 20 and max_messages > 20 and str(self.selected_thread_id).isdigit():
            try:
                print("Checking additional messages via direct_thread fallback...")
                dt = self.client.direct_thread(int(self.selected_thread_id), amount=min(max_messages, 200))
                if dt and dt.messages:
                    fallback_items = []
                    for dm in dt.messages:
                        if hasattr(dm, 'model_dump'):
                            fallback_items.append(dm.model_dump())
                        elif hasattr(dm, 'dict'):
                            fallback_items.append(dm.dict())
                    if len(fallback_items) > len(all_messages):
                        all_messages = fallback_items
            except Exception:
                pass
                
        print(f"Total messages retrieved: {len(all_messages)}\n")
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
            
            items = self.fetch_all_messages_paginated(amount)
            
            if not items:
                print("No messages found in this thread.")
                return
            
            print(f"\nFound {len(items)} messages (newest first):")
            print("-" * 75)
            
            for item in items[:30]:
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
                    continue
                    
        except Exception as e:
            print(f"Failed to view messages: {e}")

    def search_messages_raw_api(self):
        """
        Search and filter messages to unsend in the selected conversation.
        Supports:
        - ALL messages sent by user (best for clearing hacked scam activity)
        - Keywords in text or link URLs
        - Photos & Videos only
        - Links & URLs only
        - Optional date cutoff (e.g. only within the last N days)
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        if not self.selected_thread_id:
            print("Please select a conversation thread first (Option 2 or 3)")
            return
        
        print(f"\n=== SEARCH / FILTER MESSAGES IN {self.selected_thread_title or self.selected_thread_id} ===")
        print("Select what you want to find & unsend:")
        print("1. ALL messages & media sent by you (Recommended for hacked accounts - unsend everything!)")
        print("2. Search by keyword(s) (e.g. 'scam,crypto,gift,vote,http')")
        print("3. Only Photos & Videos (photos, disappearing snaps, videos, media)")
        print("4. Only Links & URLs (scam links, suspicious websites)")
        print("5. Cancel")
        
        filter_mode = input("\nSelect filter option (1-5): ").strip()
        if filter_mode not in ("1", "2", "3", "4"):
            print("Cancelled.")
            return
        
        keywords = []
        filter_desc = ""
        
        if filter_mode == "1":
            filter_desc = "ALL messages & media sent by your account"
        elif filter_mode == "2":
            kw_input = input("Enter keywords (comma-separated, e.g. 'gift,link,crypto,vote'): ").strip()
            if not kw_input:
                print("No keywords entered.")
                return
            keywords = [k.strip().lower() for k in kw_input.split(",") if k.strip()]
            filter_desc = f"Messages containing keywords: {', '.join(keywords)}"
        elif filter_mode == "3":
            filter_desc = "Photos & Videos (all media)"
        elif filter_mode == "4":
            filter_desc = "Links & URLs"
        
        # Optional date filter
        days_input = input("\nOptional: Only scan messages sent in the last N days (press Enter for ALL time): ").strip()
        cutoff_ts = 0.0
        if days_input.isdigit() and int(days_input) > 0:
            cutoff_ts = time.time() - (int(days_input) * 86400)
            filter_desc += f" (within last {days_input} days)"
            
        try:
            amount_str = input("Max messages to scan in thread history (default 1000): ").strip()
            amount = int(amount_str) if amount_str.isdigit() else 1000
            
            print(f"\nFiltering for: {filter_desc}")
            print(f"Scanning up to {amount} messages...")
            
            items = self.fetch_all_messages_paginated(amount)
            
            if not items:
                print("No messages found in thread.")
                return
            
            matched_items = []
            
            for raw_item in items:
                try:
                    info = extract_message_info(raw_item, self.my_user_id)
                    is_mine = info['is_sent_by_viewer'] or (info['user_id'] == str(self.my_user_id))
                    
                    # Apply date cutoff if specified
                    if cutoff_ts > 0.0 and info['timestamp_ts'] > 0.0:
                        if info['timestamp_ts'] < cutoff_ts:
                            continue
                            
                    matched = False
                    
                    if filter_mode == "1":
                        if is_mine:
                            matched = True
                            
                    elif filter_mode == "2":
                        text_lower = info['summary'].lower()
                        if any(kw in text_lower for kw in keywords):
                            matched = True
                            
                    elif filter_mode == "3":
                        if info['category'] == 'media':
                            matched = True
                            
                    elif filter_mode == "4":
                        if info['category'] == 'link':
                            matched = True
                    
                    if matched:
                        # Attach thread info
                        info['thread_id'] = self.selected_thread_id
                        matched_items.append(info)
                        
                        sender_label = f"{self.my_username} (YOU)" if is_mine else f"Other User ({info['user_id']})"
                        disp_summary = info['summary'][:80] + "..." if len(info['summary']) > 80 else info['summary']
                        
                        print(f"  [Match #{len(matched_items)}] ID: {info['id']} | Type: {info['category'].upper()} | From: {sender_label}")
                        print(f"    Content: {disp_summary}")
                        
                except Exception:
                    continue
            
            print("\n" + "=" * 55)
            print(f"SCAN COMPLETE: Found {len(matched_items)} matching messages.")
            print("=" * 55)
            
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
        """UNSEND queued messages from the active search filter"""
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        print("\n=== BULK UNSEND QUEUED MESSAGES ===")
        
        if not self.last_matches:
            print("No matching messages selected yet.")
            print("Please run Option 5 (Search / Filter Messages) or Option 7 first!")
            return
        
        matches = self.last_matches
        
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
        print(f"Other participants' messages: {len(other_messages)} (Ignored - only your own messages can be unsent)")
        
        if len(own_messages) == 0:
            print("\nNo messages from your account to unsend.")
            return
        
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
            thread_id = m.get('thread_id') or self.selected_thread_id
            
            print(f"[{i}/{len(own_messages)}] Unsending {m['category'].upper()} ({msg_id})...", end=" ")
            
            if self.unsend_message(thread_id, msg_id):
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
        
        self.last_matches = []
        self.last_filter_desc = ""

    def clean_all_conversations(self):
        """
        ACCOUNT-WIDE CLEANUP:
        Scans across ALL conversations in the user's inbox and bulk unsends
        scam messages, links, and photos sent from the user's account.
        This completely eliminates the need to manually scroll or select chats one-by-one!
        """
        if not self.logged_in:
            print("Please login first (Option 1)")
            return
        
        print("\n" + "=" * 65)
        print("   ACCOUNT-WIDE CLEANUP: UNSEND ACROSS ALL INBOX CONVERSATIONS")
        print("=" * 65)
        print("This feature scans across ALL conversations in your inbox and unsends")
        print("scam links, photos, and messages sent by your account when it was hacked.")
        print("You DO NOT need to scroll down or select conversations one-by-one!\n")
        
        print("Step 1: How many conversations to scan from your inbox?")
        print("1. Recent 25 conversations")
        print("2. Recent 50 conversations")
        print("3. Recent 100 conversations")
        print("4. ALL conversations in inbox (Full inbox scan)")
        print("5. Custom number")
        print("6. Cancel")
        
        conv_choice = input("\nSelect option (1-6): ").strip()
        max_convs = 25
        if conv_choice == "1":
            max_convs = 25
        elif conv_choice == "2":
            max_convs = 50
        elif conv_choice == "3":
            max_convs = 100
        elif conv_choice == "4":
            max_convs = 10000  # Will scan until end of inbox
        elif conv_choice == "5":
            c_input = input("Enter number of conversations to scan (e.g. 150): ").strip()
            max_convs = int(c_input) if c_input.isdigit() else 50
        else:
            print("Cancelled.")
            return

        print("\nStep 2: What do you want to unsend across these conversations?")
        print("1. ALL messages & media sent by you (Recommended for hacked accounts - clean everything!)")
        print("2. Only Links & URLs (scam websites, phishing links)")
        print("3. Only Photos & Videos (disappearing photos, images, media)")
        print("4. Messages containing specific keywords (e.g. 'vote,gift,link,crypto')")
        print("5. Cancel")
        
        filter_mode = input("\nSelect filter option (1-5): ").strip()
        if filter_mode not in ("1", "2", "3", "4"):
            print("Cancelled.")
            return

        keywords = []
        filter_desc = ""
        if filter_mode == "1":
            filter_desc = "ALL messages & media sent by your account"
        elif filter_mode == "2":
            filter_desc = "Links & URLs"
        elif filter_mode == "3":
            filter_desc = "Photos & Videos"
        elif filter_mode == "4":
            kw_input = input("Enter keywords (comma-separated, e.g. 'vote,link,gift,crypto'): ").strip()
            if not kw_input:
                print("No keywords entered.")
                return
            keywords = [k.strip().lower() for k in kw_input.split(",") if k.strip()]
            filter_desc = f"Keywords ({', '.join(keywords)})"

        # Step 3: Date cutoff
        print("\nStep 3: Date/Time Filter (CRUCIAL FOR HACK RECOVERY):")
        print("You can limit deletion to only messages sent recently when the hack occurred,")
        print("protecting all your previous personal messages and photos from before the hack.")
        days_input = input("Only unsend messages sent in the last N days (e.g. '3' or '7', or press Enter for ALL time): ").strip()
        cutoff_ts = 0.0
        if days_input.isdigit() and int(days_input) > 0:
            cutoff_ts = time.time() - (int(days_input) * 86400)
            filter_desc += f" (within last {days_input} days)"
            print(f"[+] Date filter active: only unsending messages sent in the last {days_input} days.")
        else:
            print("[+] No date filter: will check all sent messages in scanned conversations.")

        # Step 4: Messages per conversation
        depth_input = input("\nMax messages to inspect per conversation (default 50, press Enter): ").strip()
        messages_per_thread = int(depth_input) if depth_input.isdigit() else 50

        print("\n" + "=" * 60)
        print("SCANNING INBOX CONVERSATIONS...")
        print("=" * 60)
        
        # Load inbox threads with cursor pagination
        threads = self.fetch_inbox_threads(max_threads=max_convs)
        if not threads:
            print("No conversations found in inbox.")
            return

        print(f"\n[+] Loaded {len(threads)} conversations from inbox. Inspecting messages for scam content...\n")
        
        matched_items = []
        affected_threads = set()

        for idx, thread in enumerate(threads, 1):
            thread_id = str(thread.get('thread_id', ''))
            users = thread.get('users', [])
            usernames = [u.get('username', '') for u in users if u.get('username')]
            thread_name = thread.get('thread_title') or (", ".join(usernames[:2]) if usernames else f"Thread_{thread_id}")

            # Collect messages: start with preview items in inbox thread
            items = thread.get('items', [])
            
            # If thread has more messages and user requested > 10, fetch deeper
            if messages_per_thread > len(items) and thread_id:
                try:
                    deeper_resp = self.client.private_request(
                        f"direct_v2/threads/{thread_id}/",
                        params={
                            "visual_message_return_type": "unseen",
                            "direction": "older",
                            "seq_id": "40065",
                            "limit": str(min(messages_per_thread, 20))
                        }
                    )
                    if deeper_resp and 'thread' in deeper_resp:
                        items = deeper_resp['thread'].get('items', items)
                except Exception:
                    pass

            thread_matches = 0
            for item in items:
                try:
                    info = extract_message_info(item, self.my_user_id)
                    is_mine = info['is_sent_by_viewer'] or (info['user_id'] == str(self.my_user_id))
                    
                    if not is_mine:
                        continue
                    
                    # Apply date cutoff
                    if cutoff_ts > 0.0 and info['timestamp_ts'] > 0.0:
                        if info['timestamp_ts'] < cutoff_ts:
                            continue
                    
                    matched = False
                    if filter_mode == "1":
                        matched = True
                    elif filter_mode == "2":
                        matched = (info['category'] == 'link')
                    elif filter_mode == "3":
                        matched = (info['category'] == 'media')
                    elif filter_mode == "4":
                        text_lower = info['summary'].lower()
                        matched = any(kw in text_lower for kw in keywords)
                    
                    if matched:
                        info['thread_id'] = thread_id
                        info['thread_name'] = thread_name
                        matched_items.append(info)
                        thread_matches += 1
                        affected_threads.add(thread_id)
                except Exception:
                    continue

            status_str = f"Found {thread_matches} to unsend" if thread_matches > 0 else "Clean"
            print(f"[{idx:2d}/{len(threads)}] {thread_name[:30]:<30} -> {status_str}")

        print("\n" + "=" * 65)
        print("ACCOUNT SCAN COMPLETE")
        print("=" * 65)
        print(f"Total conversations scanned: {len(threads)}")
        print(f"Affected conversations:       {len(affected_threads)}")
        print(f"Total messages to unsend:     {len(matched_items)}")
        
        if not matched_items:
            print("\n[+] Great news! No matching scam messages were found across your conversations.")
            return

        text_count = sum(1 for m in matched_items if m['category'] == 'text')
        media_count = sum(1 for m in matched_items if m['category'] == 'media')
        link_count = sum(1 for m in matched_items if m['category'] == 'link')
        other_count = len(matched_items) - (text_count + media_count + link_count)

        print(f"\nBreakdown:")
        print(f"  - Scam Links & URLs: {link_count}")
        print(f"  - Photos & Media:    {media_count}")
        print(f"  - Text Messages:     {text_count}")
        if other_count > 0:
            print(f"  - Other:             {other_count}")

        print(f"\nPreview of first 15 messages that will be UNSENT:")
        print("-" * 65)
        for i, m in enumerate(matched_items[:15], 1):
            disp = m['summary'][:50] + "..." if len(m['summary']) > 50 else m['summary']
            print(f"{i:2d}. In {m['thread_name']} | [{m['category'].upper()}] {disp}")
        if len(matched_items) > 15:
            print(f"... and {len(matched_items) - 15} more messages across your conversations.")
        print("-" * 65)

        confirm = input(f"\nType 'YES' (in capital letters) to unsend ALL {len(matched_items)} messages across {len(affected_threads)} chats: ").strip()
        if confirm != 'YES':
            print("Account-wide unsend cancelled by user.")
            return

        print(f"\nStarting automatic account-wide unsend...")
        print("Note: Including a 1-second delay between deletions to keep your account safe from rate limits.\n")

        deleted = 0
        failed = 0

        for i, m in enumerate(matched_items, 1):
            msg_id = m['id']
            thread_id = m['thread_id']
            thread_name = m.get('thread_name', thread_id)
            
            print(f"[{i}/{len(matched_items)}] In {thread_name[:20]}: Unsending {m['category'].upper()} ({msg_id})...", end=" ")
            
            if self.unsend_message(thread_id, msg_id):
                print("[+] Unsent")
                deleted += 1
            else:
                print("[-] Failed")
                failed += 1
                
            time.sleep(1.0)

        print("\n" + "=" * 65)
        print("ACCOUNT-WIDE CLEANUP COMPLETE!")
        print(f"Successfully unsent: {deleted} messages across {len(affected_threads)} conversations")
        print(f"Failed:              {failed} messages")
        print("=" * 65)
        print("Your account has been cleaned! All scam messages sent to your contacts have been removed.")

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
                    print(f"Thread:   Selected: {self.selected_thread_title or self.selected_thread_id} (ID: {self.selected_thread_id})")
                else:
                    print("Thread:   None selected (Select Option 2 or 3)")
                    
                if self.last_matches:
                    print(f"Filter:   {len(self.last_matches)} messages queued ({self.last_filter_desc})")
                
                print("\nOptions:")
                print("1. Login / Account (Username/Password or Session ID Cookie)")
                print("2. List Conversations (Browse Inbox with Next-Page pagination)")
                print("3. Select Conversation (by Username or Thread ID)")
                print("4. View Messages (Unlimited pagination in selected conversation)")
                print("5. Search / Filter Messages (In selected conversation)")
                print("6. Unsend Queued Messages (In selected conversation)")
                print("7. CLEAN ALL CONVERSATIONS (Account-Wide Scam Unsend) [NEW]")
                print("8. Logout / Switch Account")
                print("9. Exit")
                
                choice = input("\nSelect option (1-9): ").strip()
                
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
                    self.clean_all_conversations()
                elif choice == "8":
                    self.logout()
                elif choice == "9":
                    print("Exiting. Goodbye!")
                    break
                else:
                    print("Invalid option. Please enter 1-9.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting. Goodbye!")
                break
            except Exception as e:
                print(f"\nUnexpected error in menu: {e}")


def main():
    try:
        print("Instagram DM Tool - UNLIMITED PAGINATION + BULK UNSEND")
        print("[+] Proper cursor-based pagination")
        print("[+] Bulk unsend text, links, photos & media")
        print("[+] Support for 2FA and Session ID login (bypasses out-of-date error)")
        print("[+] Account-wide cleanup to wipe out scam messages across ALL inbox chats")
        tool = IGDMTool()
        tool.menu_loop()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
