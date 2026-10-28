#!/usr/bin/env python3
"""
Comprehensive unit tests for instagram_dm_tool.py
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

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
            # First call without verification_code raises TwoFactorRequired
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
                # Verify second login call included verification_code="123456"
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


if __name__ == "__main__":
    unittest.main()
