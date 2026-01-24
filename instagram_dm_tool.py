#!/usr/bin/env python3
"""
instagram_dm_tool.py
Modern Instagram DM Tool with Rich UI
"""

import os
import sys
import json
import time
import webbrowser
from datetime import datetime
from typing import Any, Dict, List, Optional

# Rich Imports
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich import print as rprint
except ImportError:
    print("ERROR: 'rich' library not installed. Please install it:")
    print("pip install rich")
    sys.exit(1)

try:
    from instagrapi import Client
except ImportError:
    print("ERROR: 'instagrapi' not installed.")
    print("pip install instagrapi")
    sys.exit(1)

# Initialize Console
console = Console()

# Constants
SESSION_FILE = "session.json"

class IGDMTool:
    def __init__(self):
        self.client = Client()
        self.logged_in = False
        self.selected_thread_id = None
        self.my_username = None
        self.my_user_id = None
        self.last_matches = []
        self.last_keywords = []

    def _get_password(self):
        """Get password input securely"""
        return Prompt.ask("Instagram password", password=True)

    def load_session(self) -> bool:
        """Load session"""
        if not os.path.exists(SESSION_FILE):
            return False
        try:
            self.client.load_settings(SESSION_FILE)
            self.client.account_info()
            return True
        except:
            return False

    def save_session(self) -> bool:
        """Save session"""
        try:
            self.client.dump_settings(SESSION_FILE)
            return True
        except:
            return False

    def login(self):
        """Login to Instagram"""
        console.print(Panel("Login to Instagram", style="bold blue"))
        
        # Try existing session
        if self.load_session():
            try:
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)
                console.print(f"[green]✓ Loaded session for: {self.my_username}[/green]")
                self.logged_in = True
                return True
            except:
                console.print("[yellow]Session invalid or expired.[/yellow]")
        
        # Fresh login
        username = Prompt.ask("Instagram username")
        if not username:
            return False
        
        password = self._get_password()
        if not password:
            return False
        
        try:
            with console.status("[bold green]Logging in...[/bold green]"):
                self.client.login(username, password)
                
                user_info = self.client.account_info()
                self.my_username = user_info.username
                self.my_user_id = str(user_info.pk)
                
                self.save_session()
            
            console.print(f"[green]✓ Logged in as: {self.my_username}[/green]")
            self.logged_in = True
            return True
        except Exception as e:
            console.print(f"[bold red]Login failed:[/bold red] {e}")
            return False
    
    def analyze_source(self, item: Dict) -> str:
        """Analyze message metadata to guess the source"""
        client_context = item.get('client_context') or ''
        
        if not client_context:
            return "Unknown"
            
        # Heuristic: Mobile apps usually use UUIDs (8-4-4-4-12 chars)
        # Web/Bots often use long numeric strings (timestamps)
        if len(client_context) > 20 and '-' in client_context:
            return "Mobile App (Likely)"
        elif client_context.isdigit():
            return "Web/Bot (Likely)"
        
        return "Unknown"

    def get_message_summary(self, item: Dict) -> str:
        """Get string summary of message item including media types and IDs"""
        item_type = item.get('item_type')
        
        if item_type == 'text':
            return item.get('text', '')
        
        elif item_type == 'media':
            media = item.get('media', {})
            media_type = media.get('media_type')
            media_id = media.get('id', '') or media.get('pk', '')
            
            suffix = f" ID:{media_id}" if media_id else ""
            
            if media_type == 1:
                return f"[Photo{suffix}]"
            elif media_type == 2:
                return f"[Video{suffix}]"
            return f"[Media{suffix}]"
            
        elif item_type == 'media_share':
            media = item.get('media_share', {})
            media_id = media.get('id', '') or media.get('pk', '')
            suffix = f" ID:{media_id}" if media_id else ""
            return f"[Post Share{suffix}]"
            
        # Other types
        type_map = {
            'voice_media': "[Voice Message]",
            'like': "[Like]",
            'raven_media': "[View Once Media]",
            'clip': "[Reel]",
            'placeholder': item.get('placeholder', {}).get('message', '[Placeholder]')
        }
        
        if item_type in type_map:
            return type_map[item_type]
            
        if item_type == 'link':
            link_text = item.get('link', {}).get('text', '')
            return f"[Link] {link_text}"
            
        return item.get('text') or f"[{item_type}]"

    def list_threads_raw_api(self):
        """List threads with a Table"""
        if not self.logged_in:
            console.print("[red]Please login first[/red]")
            return False
        
        try:
            with console.status("[bold cyan]Fetching threads...[/bold cyan]"):
                response = self.client.private_request("direct_v2/inbox/", params={
                    "visual_message_return_type": "unseen",
                    "thread_message_limit": "2",
                    "persistentBadging": "true",
                    "limit": "20"
                })
            
            if not response or 'inbox' not in response:
                console.print("[red]No inbox data received[/red]")
                return False
            
            inbox = response['inbox']
            threads = inbox.get('threads', [])
            
            if not threads:
                console.print("[yellow]No threads found[/yellow]")
                return False
            
            # Create Table
            table = Table(title="Recent Conversations", show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Users", style="cyan")
            table.add_column("Last Message", style="white")
            table.add_column("Thread ID", style="dim")
            
            for i, thread in enumerate(threads, 1):
                try:
                    thread_id = thread.get('thread_id', 'Unknown')
                    users = thread.get('users', [])
                    usernames = [u['username'] for u in users[:3] if 'username' in u]
                    users_str = ", ".join(usernames) if usernames else "Unknown"
                    
                    items = thread.get('items', [])
                    last_msg = ""
                    if items:
                        last_msg = self.get_message_summary(items[0])
                        # Truncate
                        if len(last_msg) > 40: last_msg = last_msg[:37] + "..."
                    
                    table.add_row(str(i), users_str, last_msg, str(thread_id))
                    
                except Exception:
                    continue
            
            console.print(table)
            
            choice = Prompt.ask("Select thread number", default="")
            if choice and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(threads):
                    self.selected_thread_id = threads[idx].get('thread_id')
                    console.print(f"[green]✓ Selected:[/green] {channels_str if 'channels_str' in locals() else 'Thread'} {self.selected_thread_id}")
                    return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]Error listing threads: {e}[/red]")
            return False

    def fetch_threads_paginated(self, max_threads=100) -> List[Dict]:
        """Fetch multiple pages of threads"""
        all_threads = []
        cursor = None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task(f"Fetching {max_threads} threads...", total=max_threads)
            
            while len(all_threads) < max_threads:
                try:
                    params = {
                        "visual_message_return_type": "unseen",
                        "thread_message_limit": "2",
                        "limit": "20"
                    }
                    if cursor: params["cursor"] = cursor
                    
                    response = self.client.private_request("direct_v2/inbox/", params=params)
                    inbox = response.get('inbox', {})
                    threads = inbox.get('threads', [])
                    
                    if not threads: break
                    
                    all_threads.extend(threads)
                    progress.update(task, advance=len(threads), description=f"fetched {len(all_threads)} threads")
                    
                    cursor = inbox.get('oldest_cursor')
                    if not cursor: break
                    
                    time.sleep(0.5)
                    if len(all_threads) >= max_threads: break
                    
                except Exception:
                    break
                    
        return all_threads[:max_threads]

    def fetch_all_messages_paginated(self, max_messages=5000):
        all_messages = []
        cursor = None
        page = 1
        consecutive_empty = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task(f"Fetching messages...", total=None)
            
            while len(all_messages) < max_messages and consecutive_empty < 3:
                try:
                    params = {"visual_message_return_type": "unseen", "direction": "older", "limit": "75"}
                    if cursor: params["cursor"] = cursor
                    
                    response = self.client.private_request(f"direct_v2/threads/{self.selected_thread_id}/", params=params)
                    items = response.get('thread', {}).get('items', [])
                    
                    if not items:
                        consecutive_empty += 1
                        time.sleep(1)
                        continue
                        
                    consecutive_empty = 0
                    all_messages.extend(items)
                    progress.update(task, description=f"Fetched {len(all_messages)} messages (Page {page})")
                    
                    # Pagination Logic
                    thread = response.get('thread', {})
                    cursor = thread.get('oldest_cursor') or thread.get('next_cursor')
                    if not cursor and items:
                        # Fallback to timestamp
                        last = items[-1]
                        cursor = last.get('timestamp')
                        if not cursor:
                            # Fallback to item_id
                            cursor = last.get('item_id') or last.get('id')
                            
                    if not cursor:
                        # Try one more just in case
                        if page == 1: 
                            page += 1
                            continue
                        break
                        
                    page += 1
                    time.sleep(0.5)
                    
                except Exception:
                    break
                    
        return all_messages[:max_messages]

    def view_messages_raw_api(self):
        """View messages in a Table"""
        if not self.logged_in: 
            console.print("[red]Login required[/red]")
            return

        if not self.selected_thread_id:
            if not self.list_threads_raw_api(): return

        amount = int(Prompt.ask("Number of messages", default="20"))
        show_raw = Confirm.ask("Show full raw JSON details?")
        
        items = []
        if amount > 75:
            items = self.fetch_all_messages_paginated(amount)
        else:
            with console.status("Fetching messages..."):
                response = self.client.private_request(f"direct_v2/threads/{self.selected_thread_id}/", params={
                    "limit": str(amount), "direction": "older"
                })
                items = response.get('thread', {}).get('items', [])

        if not items:
            console.print("[yellow]No messages found.[/yellow]")
            return

        # Render Table
        table = Table(title=f"Messages in {self.selected_thread_id}", show_lines=True)
        table.add_column("Date", style="dim", width=19)
        table.add_column("From", style="cyan", width=15)
        table.add_column("Source", style="magenta", width=10)
        table.add_column("Content")
        
        for item in items[:amount]: # Limit display if fetched many
            try:
                ts = item.get('timestamp')
                try:
                    date_str = datetime.fromtimestamp(int(ts)/1000000).strftime("%Y-%m-%d %H:%M:%S")
                except: date_str = str(ts)
                
                user_id = str(item.get('user_id'))
                sender = "YOU" if user_id == self.my_user_id else f"ID:{user_id}"
                
                source = self.analyze_source(item)
                text = self.get_message_summary(item)
                
                table.add_row(date_str, sender, source, text)
                
                if show_raw:
                    clean = item.copy()
                    if 'xma_share' in clean: clean['xma_share'] = '<truncated>'
                    console.print(Panel(json.dumps(clean, indent=2), title="Raw JSON", style="dim"))
            except: pass
            
        console.print(table)

    def bulk_unsend_all_threads(self):
        """Bulk unsend with progress bars"""
        if not self.logged_in: return

        console.print(Panel("BULK UNSEND - Scan multiple conversations and delete matches", style="bold red"))
        
        keywords_str = Prompt.ask("Keywords/IDs to match")
        if not keywords_str: return
        keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
        
        max_threads = int(Prompt.ask("Max threads to scan", default="50"))
        msgs_per_thread = int(Prompt.ask("Messages per thread", default="20"))
        
        threads = self.fetch_threads_paginated(max_threads)
        
        matches = []
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            scan_task = progress.add_task("Scanning for matches...", total=len(threads))
            
            for thread in threads:
                progress.advance(scan_task)
                t_id = thread.get('thread_id')
                users = thread.get('users', [])
                name = users[0].get('username') if users else "Unknown"
                
                items = thread.get('items', [])
                for item in items[:msgs_per_thread]:
                    if str(item.get('user_id')) != self.my_user_id: continue
                    
                    summary = self.get_message_summary(item)
                    if any(k in summary.lower() for k in keywords):
                        matches.append({
                            "thread_id": t_id,
                            "thread_name": name,
                            "msg": item,
                            "summary": summary
                        })
        
        console.print(f"\n[bold green]Found {len(matches)} matching messages.[/bold green]")
        if not matches: return
        
        # Preview
        preview_table = Table(title="Preview Matches", show_header=False)
        for m in matches[:5]:
            preview_table.add_row(f"To [cyan]{m['thread_name']}[/cyan]: {m['summary']}")
        console.print(preview_table)
        if len(matches) > 5: console.print(f"... and {len(matches)-5} more")
        
        if not Confirm.ask(f"[bold red]Unsend {len(matches)} messages?[/bold red]"):
            console.print("Cancelled.")
            return
            
        # Delete loop
        with Progress(TextColumn("{task.description}"), SpinnerColumn()) as progress:
            del_task = progress.add_task("Deleting...", total=len(matches))
            deleted = 0
            
            for m in matches:
                try:
                    t_id = m['thread_id']
                    msg = m['msg']
                    msg_id = msg.get('item_id') or msg.get('id')
                    
                    progress.update(del_task, description=f"Unsending from {m['thread_name']}...")
                    
                    self.client.private_request(
                        f"direct_v2/threads/{t_id}/items/{msg_id}/delete/",
                        data={"_uuid": self.client.uuid, "_uid": self.my_user_id},
                        with_signature=False
                    )
                    deleted += 1
                    progress.advance(del_task)
                    time.sleep(1.5)
                except Exception:
                    time.sleep(2)
        
        console.print(f"[bold green]Done. Unsent {deleted} messages.[/bold green]")

    def check_login_activity(self):
        """Show login activity in a Table"""
        if not self.logged_in: return
        
        with console.status("Fetching login activity..."):
            try:
                try:
                    result = self.client.private_request("accounts/login_activity/")
                except:
                    result = self.client.private_request("session/login_activity/")
                
                sessions = result.get('active_sessions') or result.get('sessions') or []
                suspicious = result.get('suspicious_logins', [])
                
                table = Table(title="Login Activity", show_lines=True)
                table.add_column("Device", style="cyan")
                table.add_column("Location", style="yellow")
                table.add_column("IP")
                table.add_column("Time", style="dim")
                table.add_column("Status")
                
                for s in sessions:
                    ts = s.get('timestamp')
                    t_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else "?"
                    is_current = "[bold green]THIS DEVICE[/bold green]" if s.get('is_current') else "Active"
                    
                    table.add_row(
                        s.get('device', '?'),
                        s.get('location', '?'),
                        s.get('ip_address', '?'),
                        t_str,
                        is_current
                    )
                
                for s in suspicious:
                    ts = s.get('timestamp')
                    t_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else "?"
                    table.add_row(
                        s.get('device', '?'),
                        s.get('location', '?'),
                        s.get('ip_address', '?'),
                        t_str,
                        "[bold red]BLOCKED[/bold red]"
                    )
                    
                console.print(table)
                
            except Exception as e:
                console.print(f"[red]Failed to get activity: {e}[/red]")

    def print_security_checklist(self):
        """Security advice Markdown"""
        md = """
# CRITICAL SECURITY ADVICE

**BASED ON YOUR SITUATION:**
The message you found had a 'Web/Automation' source.
This strongly suggests a **Third-Party App** or **Bot Service** has your credential.
Examples: 'Follower Trackers', 'Story Downloaders', or 'Auto-Liker' services.

## IMMEDIATE ACTIONS

1. **[CRITICAL] CHANGE YOUR PASSWORD NOW.**
   - This is the ONLY way to instantly log out all other people/bots.
   
2. **[CRITICAL] ENABLE 2-FACTOR AUTHENTICATION.**
   - Use an Authenticator App (like Google Auth), NOT just SMS.

3. **Revoke 'Apps and Websites' Permissions.**
   - Settings -> Security -> Apps and Websites.
   - Remove anything active that you don't 100% trust.
"""
        console.print(Markdown(md))
        
        if Confirm.ask("Open Password Settings in Browser?"):
             webbrowser.open("https://www.instagram.com/accounts/password/change/")
             
        if Confirm.ask("Open 2FA Settings?"):
            webbrowser.open("https://www.instagram.com/accounts/two_factor_authentication/")
            
        if Confirm.ask("Open Apps/Websites Settings?"):
            webbrowser.open("https://www.instagram.com/accounts/manage_access/")

    def menu_loop(self):
        while True:
            console.print("\n")
            console.rule("[bold magenta]INSTAGRAM DM TOOL[/bold magenta]")
            
            if self.logged_in:
                console.print(f"[dim]Logged in as: [cyan]{self.my_username}[/cyan][/dim]")
            
            options = {
                "1": "Login",
                "2": "Bulk Unsend (All Threads)",
                "3": "View Login Activity",
                "4": "View Messages (Debug Mode)",
                "5": "Security Advice",
                "6": "Exit"
            }
            
            for k, v in options.items():
                console.print(f"[bold cyan]{k}.[/bold cyan] {v}")
            
            choice = Prompt.ask("Select option", choices=list(options.keys()))
            
            if choice == "1": self.login()
            elif choice == "2": self.bulk_unsend_all_threads()
            elif choice == "3": self.check_login_activity()
            elif choice == "4": self.view_messages_raw_api()
            elif choice == "5": self.print_security_checklist()
            elif choice == "6": 
                console.print("[green]Goodbye![/green]")
                break

if __name__ == "__main__":
    try:
        tool = IGDMTool()
        tool.menu_loop()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal Error: {e}[/red]")
