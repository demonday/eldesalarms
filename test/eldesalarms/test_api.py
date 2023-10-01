import unittest
from unittest.mock import patch, Mock
from eldesalarms import UserSession, DeviceApi, User
from datetime import datetime, date


class TestDeviceApi(unittest.TestCase):

    @patch.object(UserSession, 'login')
    def setUp(self, mock_login):
        mock_login.return_value = True
        self.session = UserSession(username="test_user", password="test_pass")
        self.device_api = DeviceApi(user_session=self.session, device_id=1)

    @patch.object(UserSession, 'get')
    def test_users_successful(self, mock_get):
        # Mock the response content for a successful get
        mock_response = Mock()
        mock_response.content = b'<html><table class="items"><tbody><tr><td>User1</td><td>Phone1</td></tr><tr>output<td></tbody></table></html>'
        mock_get.return_value = mock_response

        # Call the method and assert the expected outcome
        users = list(self.device_api.users)
        self.assertEqual(len(users), 1)
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
        self.assertIsNone(log_entry.apt_no)

    @patch.object(UserSession, 'get')
    @patch.object(UserSession, 'post')
    def test_add_user_successful(self, mock_post, mock_get):
        # Mock the responses for get and post requests
        mock_get_response = Mock()
        mock_get_response.content = b'<html><form action="/action_url"></form></html>'
        mock_get.return_value = mock_get_response

        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post.return_value = mock_post_response

        # Call the method and assert the expected outcome
        user = User(name='TestUser', phone='1234567890')
        self.device_api.add_user(user)
        mock_post.assert_called_once()

    @patch.object(UserSession, 'get')
    def test_get_logs_successful(self, mock_get):
        # Mock the response content for a successful get
        mock_response = Mock()
        mock_response.text = '2023.09.23 20:08:56 Opened by user:18TVName(callR:1):0871234567\n'
        mock_get.return_value = mock_response

        # Call the method and assert the expected outcome
        start_date = date(2023, 9, 23)
        end_date = date(2023, 9, 24)
        logs = self.device_api.get_logs(start=start_date, end=end_date)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].who, '18TVName')

# Add more test methods to cover other methods and branches in the DeviceApi class


@patch.object(UserSession, 'get')
@patch.object(UserSession, 'post')
def test_add_user_successful(self, mock_post, mock_get):
    # Mocking the GET response to simulate loading the add user page
    mock_get_response = Mock()
    mock_get_response.content = b'<html><form action="/action_url"></form></html>'
    mock_get.return_value = mock_get_response

    # Mocking the POST response to simulate successfully adding a user
    mock_post_response = Mock()
    mock_post_response.status_code = 200  # Assuming 200 means success
    mock_post.return_value = mock_post_response

    # Defining a user object to be added
    user = User(name='TestUser', phone='1234567890', output='TestOutput')

    # Calling the add_user method
    try:
        self.device_api.add_user(user)
    except Exception as e:
        self.fail(f"add_user raised {type(e)} unexpectedly!")

    # Verifying that the POST request was called with the expected URL and data
    # You need to replace the expected_url and expected_data with the actual values you expect
    expected_url = '/action_url'  # Replace this with the actual URL
    expected_data = {  # Replace these with the actual parameters
        'YII_CSRF_TOKEN': self.session.token,
        'GatesconfigDeviceUsersdatabase[phone]': '1234567890',
        'GatesconfigDeviceUsersdatabase[user_name]': 'TestUser',
        'GatesconfigDeviceUsersdatabase[output]': 'TestOutput',
        # ... other parameters ...
    }
    mock_post.assert_called_once_with(
        url=expected_url, data=expected_data, headers=any)


@patch.object(UserSession, 'get')
@patch.object(UserSession, 'post')
def test_add_user_failure(self, mock_post, mock_get):
    # Mocking the GET response as before
    mock_get_response = Mock()
    mock_get_response.content = b'<html><form action="/action_url"></form></html>'
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
