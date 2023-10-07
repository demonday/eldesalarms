import re
import unittest
from unittest import mock
from unittest.mock import PropertyMock, patch, Mock, call
from eldesalarms.session import UserSession
from eldesalarms.api import DeviceApi, LogEntry, User
from datetime import datetime, date

users_page_html_str = (
    "<html>"
    "  <body>"
    "    <div>"
    "      <!-- div[1] -->"
    "      <section>"
    "        <div>"
    "          <!-- div[1] -->"
    "          <div>"
    "            <div>"
    "              <div></div><div></div><div></div>"
    "              <div>"
    "                <!-- div[4] -->"
    "                <div>"
    "                  <div></div>"
    "                  <div>"
    "                    <!-- div[2] -->"
    "                    <div></div><div></div><div></div><div></div>"
    "                    <div>"
    "                      <!-- div[5] -->"
    "                      <div>"
    "                        <div></div>"
    "                        <div>"
    "                          <!-- div[2] -->"
    "                          <ul>"
    "                            <li /><li /><li /><li /><li /><li /><li /><li /><li /><li /><li />"
    "                            <li>"
    "                              <!-- li[12] -->"
    "                              <a href='https://gates.eldesalarms.com/en/configDeviceUsersdatabase_page/1.html'>1</a>"
    "                            </li>"
    "                          </ul>"
    "                          <table class=\"items table table-striped table-condensed\">"
    "                            <tr><td>User1</td><td>Phone1</td><td>output</td></tr>"
    "                            <tr><td>User2</td><td>Phone2</td><td>output</td></tr>"
    "                            <tr><td>User3</td><td>Phone3</td><td>output</td></tr>"
    "                            <tr><td>User4</td><td>Phone4</td><td>output</td></tr>"
    "                            <tr><td>User5</td><td>Phone5</td><td>output</td></tr>"
    "                            <tr><td>User6</td><td>Phone6</td><td>output</td></tr>"
    "                            <tr><td>User7</td><td>Phone7</td><td>output</td></tr>"
    "                            <tr><td>User8</td><td>Phone8</td><td>output</td></tr>"
    "                            <tr><td>User9</td><td>Phone9</td><td>output</td></tr>"
    "                            <tr><td>User10</td><td>Phone10</td><td>output</td></tr>"
    "                          </table>"
    "                        </div>"
    "                      </div>"
    "                    </div>"
    "                  </div>"
    "                </div>"
    "              </div>"
    "            </div>"
    "          </div>"
    "        </div>"
    "      </section>"
    "      <div></div>"
    "    </div>"
    "  </body>"
    "</html>"
)

add_user_form = (
    "<html>"
    "  <body>"
    "    <form action='/action_url'></form>"
    "    <div class='controls'>"
    "      <select class='app_access_select' name='GatesconfigDeviceUsersdatabase[output]' id='GatesconfigDeviceUsersdatabase_output'>"
    "        <option value='1' selected='selected'>TestOutput</option>"
    "        <option value='2'>controller2</option>"
    "        <option value='3'>All</option>"
    "       </select>"
    "    </div>"
    "  </body>"
    "</html>"
)


class TestDeviceApi(unittest.TestCase):

    @patch.object(UserSession, 'login')
    def setUp(self, mock_login):
        mock_login.return_value = True
        self.session = UserSession(username="test_user", password="test_pass")
        self.session.token = 'test_token'
        self.device_api = DeviceApi(user_session=self.session, device_id=1)

    @patch.object(UserSession, 'get')
    def test_users(self, mock_get):
        # Mock the response content for a successful get
        mock_response = Mock()
        mock_response.content = users_page_html_str.encode('utf-8')
        mock_get.return_value = mock_response

        # Call the method and assert the expected outcome
        users = list(self.device_api.users)
        self.assertEqual(len(users), 10)
        self.assertEqual(users[0].name, 'User1')
        self.assertEqual(users[0].phone, 'Phone1')
        self.assertEqual(users[0].output, 'output')

    def test_parse_log_line(self):
        # Test the parse_log_line method with a sample log line
        line = '2023.09.23 20:08:56 Opened by user:18TVName(callR:1):0871234567'
        log_entry = DeviceApi.parse_log_line(line)
        self.assertEqual(log_entry.when, datetime.strptime(
            '2023.09.23 20:08:56', '%Y.%m.%d %H:%M:%S'))
        self.assertEqual(log_entry.who, '18TVName')
        self.assertEqual(log_entry.phone, '0871234567')
        self.assertEqual(log_entry.apt_no, 18)

    @patch.object(UserSession, 'get')
    @patch.object(UserSession, 'post')
    def test_add_user_successful(self, mock_post, mock_get):

        # Mock the responses for get and post requests
        mock_get_response = Mock()
        mock_get_response.content = add_user_form.encode('utf-8')
        mock_get.return_value = mock_get_response

        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post.return_value = mock_post_response

        # Call the method and assert the expected outcome
        user = User(name='TestUser', phone='1234567890', output='TestOutput')
        self.device_api.add_user(user)
        mock_post.assert_called_once()

    @patch.object(UserSession, 'get')
    def test_get_logs(self, mock_get):
        # Set up the mock responses
        mock_response1 = Mock()

        mock_response1.content = b'<html><body><div><div><a href="link">a1</a><a href="download_link"></a></div></div></body></html>'
        mock_response1.text = '<html><body><div><div><a href="link">a1</a><a href="download_link"></a></div></div></body></html>'
        mock_response1.status_code = 200

        mock_response2 = Mock()
        mock_response2.text = '2023.09.23 20:08:56 Opened by user:18TVperson1(call\nR:1):0871234567\n' \
                              '2023.09.23 20:09:56 Opened by user:18TVperson2(call\nR:1):0871234568\n'
        mock_response2.status_code = 200

        # Set the side effect of the mock_get to iterate over the mock responses
        mock_get.side_effect = [mock_response1, mock_response2]

        # Create a DeviceApi object with a logged-in UserSession
        user_session = UserSession(username='user', password='pass')
        user_session.logged_in = True
        device_api = DeviceApi(user_session=user_session, device_id=9999)

        # Call the get_logs method and check the returned log entries
        start_date = date(2023, 9, 23)
        end_date = date(2023, 9, 24)
        log_entries = device_api.get_logs(start=start_date, end=end_date)

        # Build expected log entries
        expected_entries = [
            LogEntry(when=datetime(2023, 9, 23, 20, 8, 56),
                     who='18TVperson1', phone='0871234567', apt_no=18),
            LogEntry(when=datetime(2023, 9, 23, 20, 9, 56),
                     who='18TVperson2', phone='0871234568', apt_no=18)
        ]

        # Assert the log entries returned by get_logs match the expected entries
        self.assertEqual(log_entries, expected_entries)

        # Assert the mock_get method was called with the correct arguments
        first_get = mock_get.call_args_list[0]
        url_called = first_get.args[0]
        expected_url_regex = r'https://gates\.eldesalarms\.com/en/gatesconfig/settings/getlog/ajax/1/device_id/9999.html\?_=\d+&logstart=2023-09-23&logend=2023-09-24'
        self.assertTrue(re.match(expected_url_regex, url_called),
                        f"Expected call to match {expected_url_regex}, but got {url_called}")

# Add more test methods to cover other methods and branches in the DeviceApi class

    @patch.object(UserSession, 'get')
    @patch.object(UserSession, 'post')
    def test_add_user_failure(self, mock_post, mock_get):
        # Mocking the GET response as before
        mock_get_response = Mock()
        mock_get_response.content = add_user_form.encode('utf-8')
        mock_get.return_value = mock_get_response

        # Mocking the POST response to simulate a failure when adding a user
        mock_post_response = Mock()
        mock_post_response.status_code = 400  # Assuming 400 means failure
        mock_post.return_value = mock_post_response

        # Defining a user object to be added
        user = User(name='TestUser', phone='1234567890', output='TestOutput')

        # Calling the add_user method and expecting a ValueError to be raised
        with self.assertRaises(ValueError):
            self.device_api.add_user(user)


if __name__ == "__main__":
    unittest.main()
