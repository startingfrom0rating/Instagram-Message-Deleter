#!/usr/bin/env python3
"""
Comprehensive unit tests for instagram_dm_tool.py
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time

# Add directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from instagram_dm_tool import (
    extract_message_info,
    load_session,
    save_session,
    IGDMTool
)
from instagrapi.exceptions import (
    TwoFactorRequired,
    ClientNeedsUpgradeError,
    ChallengeRequired
)


class TestInstagramDMTool(unittest.TestCase):

    def test_extract_message_info_text(self):
        item = {
            "item_id": "123456",
            "user_id": 99999,
            "timestamp": 1700000000000000,
            "item_type": "text",
            "text": "Hello world"
        }
        info = extract_message_info(item, my_user_id="99999")
        self.assertEqual(info["id"], "123456")
        self.assertEqual(info["user_id"], "99999")
        self.assertTrue(info["is_sent_by_viewer"])
        self.assertEqual(info["category"], "text")
        self.assertEqual(info["summary"], "Hello world")
        self.assertGreater(info["timestamp_ts"], 0.0)

    def test_extract_message_info_photo_and_video(self):
        # Photo
        item_photo = {
            "item_id": "photo_1",
            "user_id": 11111,
            "item_type": "media",
            "media": {"media_type": 1}
        }
        info_photo = extract_message_info(item_photo, my_user_id="11111")
        self.assertEqual(info_photo["category"], "media")
        self.assertEqual(info_photo["summary"], "[Photo]")
        self.assertTrue(info_photo["is_sent_by_viewer"])

        # Disappearing Snap / Raven Media
        item_snap = {
            "item_id": "snap_1",
            "user_id": 11111,
            "item_type": "raven_media",
            "visual_media": {}
        }
        info_snap = extract_message_info(item_snap, my_user_id="11111")
        self.assertEqual(info_snap["category"], "media")
        self.assertIn("Disappearing", info_snap["summary"])

    def test_extract_message_info_link(self):
        item_link = {
            "item_id": "link_1",
            "user_id": 11111,
            "item_type": "link",
            "link": {"text": "https://suspicious-scam.com/login"}
        }
        info_link = extract_message_info(item_link, my_user_id="11111")
        self.assertEqual(info_link["category"], "link")
        self.assertIn("https://suspicious-scam.com/login", info_link["summary"])

        # URL in raw text also categorized as link
        item_text_url = {
            "item_id": "link_2",
            "user_id": 11111,
            "item_type": "text",
            "text": "Vote for me please at https://scam-link.xyz"
        }
        info_text_url = extract_message_info(item_text_url, my_user_id="11111")
        self.assertEqual(info_text_url["category"], "link")

    def test_extract_message_info_other_user(self):
        item = {
            "item_id": "other_1",
            "user_id": 22222,
            "item_type": "text",
            "text": "Hey from friend"
        }
        info = extract_message_info(item, my_user_id="11111")
        self.assertFalse(info["is_sent_by_viewer"])
        self.assertEqual(info["user_id"], "22222")

    @patch("instagram_dm_tool.os.path.exists", return_value=True)
    def test_load_session_with_override_app_version(self, mock_exists):
        mock_client = MagicMock()
        success = load_session(mock_client, "dummy_session.json")
        mock_client.load_settings.assert_called_with("dummy_session.json", override_app_version=True)
        self.assertTrue(success)

    def test_tool_init(self):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            self.assertFalse(tool.logged_in)
            self.assertIsNone(tool.selected_thread_id)

    @patch("instagram_dm_tool.save_session")
    def test_login_sessionid_success(self, mock_save):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()
            mock_account = MagicMock()
            mock_account.username = "testuser"
            mock_account.pk = 123456789
            tool.client.account_info.return_value = mock_account

            with patch("builtins.input", return_value="123456789%3Atest_session_id_abcdef12345"):
                result = tool.login_sessionid()
                self.assertTrue(result)
                self.assertTrue(tool.logged_in)
                self.assertEqual(tool.my_username, "testuser")
                self.assertEqual(tool.my_user_id, "123456789")
                tool.client.login_by_sessionid.assert_called_once_with("123456789%3Atest_session_id_abcdef12345")

    @patch("instagram_dm_tool.save_session")
    def test_login_credentials_with_2fa(self, mock_save):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()
            mock_response = MagicMock()
            tool.client.login.side_effect = [
                TwoFactorRequired("2FA required", response=mock_response),
                True
            ]
            mock_account = MagicMock()
            mock_account.username = "testuser"
            mock_account.pk = 123456789
            tool.client.account_info.return_value = mock_account

            with patch("builtins.input", side_effect=["testuser", "123456"]), \
                 patch("instagram_dm_tool.get_password", return_value="testpass"):
                result = tool.login_credentials()
                self.assertTrue(result)
                self.assertTrue(tool.logged_in)
                tool.client.login.assert_called_with("testuser", "testpass", verification_code="123456")

    def test_login_credentials_handles_out_of_date_and_offers_sessionid(self):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()
            mock_response = MagicMock()
            tool.client.login.side_effect = ClientNeedsUpgradeError(
                "Your version of Instagram is out of date. Please upgrade your app to log in to Instagram.",
                response=mock_response
            )

            with patch("builtins.input", side_effect=["testuser", "n"]), \
                 patch("instagram_dm_tool.get_password", return_value="testpass"):
                result = tool.login_credentials()
                self.assertFalse(result)
                self.assertFalse(tool.logged_in)

    def test_unsend_message_endpoints(self):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()
            tool.my_user_id = "12345"

            # Primary endpoint succeeds
            tool.client.private_request.return_value = {"status": "ok"}
            self.assertTrue(tool.unsend_message("thread_1", "msg_1"))

            # Primary endpoint throws, fallback to direct_message_delete
            tool.client.private_request.side_effect = Exception("fail")
            tool.client.direct_message_delete.return_value = True
            self.assertTrue(tool.unsend_message("100", "200"))

    def test_fetch_inbox_threads_pagination(self):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()

            # Mock 2 pages of inbox threads
            page1 = {
                "inbox": {
                    "threads": [{"thread_id": "1"}, {"thread_id": "2"}],
                    "oldest_cursor": "cursor_page2"
                }
            }
            page2 = {
                "inbox": {
                    "threads": [{"thread_id": "3"}, {"thread_id": "4"}],
                    "oldest_cursor": None
                }
            }
            tool.client.private_request.side_effect = [page1, page2]

            threads = tool.fetch_inbox_threads(max_threads=10)
            self.assertEqual(len(threads), 4)
            self.assertEqual([t["thread_id"] for t in threads], ["1", "2", "3", "4"])

    def test_fetch_all_messages_paginated_multiple_pages(self):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()
            tool.selected_thread_id = "3402823668"

            page1 = {
                "thread": {
                    "items": [{"item_id": "m1"}, {"item_id": "m2"}],
                    "oldest_cursor": "cur_page2",
                    "has_older": True
                }
            }
            page2 = {
                "thread": {
                    "items": [{"item_id": "m3"}, {"item_id": "m4"}],
                    "oldest_cursor": None,
                    "has_older": False
                }
            }
            tool.client.private_request.side_effect = [page1, page2]

            messages = tool.fetch_all_messages_paginated(max_messages=10)
            self.assertEqual(len(messages), 4)
            self.assertEqual([m["item_id"] for m in messages], ["m1", "m2", "m3", "m4"])

    def test_account_wide_scan_flow(self):
        with patch.object(IGDMTool, '_check_existing_session'):
            tool = IGDMTool()
            tool.client = MagicMock()
            tool.logged_in = True
            tool.my_user_id = "12345"
            tool.my_username = "testuser"

            # Mock 2 inbox conversations, each containing a scam link sent by the user
            fake_threads = [
                {
                    "thread_id": "t1",
                    "thread_title": "Chat With Friend 1",
                    "items": [
                        {
                            "item_id": "m1",
                            "user_id": 12345,
                            "item_type": "text",
                            "text": "Vote for me: https://scam-link.com",
                            "timestamp": time.time()
                        }
                    ]
                },
                {
                    "thread_id": "t2",
                    "thread_title": "Chat With Friend 2",
                    "items": [
                        {
                            "item_id": "m2",
                            "user_id": 12345,
                            "item_type": "media",
                            "media": {"media_type": 1},
                            "timestamp": time.time()
                        }
                    ]
                }
            ]
            tool.fetch_inbox_threads = MagicMock(return_value=fake_threads)
            tool.unsend_message = MagicMock(return_value=True)

            # Option inputs:
            # 1. max_convs: "1" (25 convs)
            # 2. filter_mode: "1" (ALL messages sent by you)
            # 3. days: "" (ALL time)
            # 4. depth: "" (default 50)
            # 5. confirmation: "YES"
            with patch("builtins.input", side_effect=["1", "1", "", "", "YES"]):
                tool.clean_all_conversations()
                # Verify unsend_message was called for both messages across threads
                self.assertEqual(tool.unsend_message.call_count, 2)
                tool.unsend_message.assert_any_call("t1", "m1")
                tool.unsend_message.assert_any_call("t2", "m2")


if __name__ == "__main__":
    unittest.main()
