import unittest
from unittest.mock import PropertyMock, patch, Mock
import requests
from eldesalarms import UserSession


class TestUserSession(unittest.TestCase):

    @patch.object(requests.Session, 'get')
    @patch.object(requests.Session, 'post')
    def test_login_successful(self, mock_post, mock_get):
        # Mocking the GET response
        mock_get_response = Mock()
        type(mock_get_response).status_code = PropertyMock(return_value=200)
        mock_get_response.cookies = Mock()
        mock_get_response.cookies.get = Mock(
            return_value="dummy_value_for_PHPSESSID")

        # Mocking the POST response
        mock_post_response = Mock()
        type(mock_post_response).status_code = PropertyMock(return_value=200)
        mock_post_response.cookies = Mock()
        mock_post_response.cookies.get = Mock(
            return_value="new_dummy_value_for_PHPSESSID")

        # Mocking the expected token extraction from cookies
        mocked_cookie = Mock()
        mocked_cookie.get = Mock(return_value='dummy_token')
        mock_post_response.cookies.__getitem__ = Mock(
            return_value=mocked_cookie)

        # Setting up the mocks
        mock_get.return_value = mock_get_response
        mock_post.return_value = mock_post_response

        # Creating a UserSession instance and calling the login method
        user_session = UserSession(username="test_user", password="test_pass")
        login_success = user_session.login()

        # Verifying the login success and token assignment
        self.assertTrue(login_success)
        self.assertEqual(user_session.token, "dummy_token")

    @patch.object(requests.Session, 'get')
    def test_login_failed_get_request(self, mock_get):
        # Mocking a failed GET response
        mock_get_response = Mock()
        type(mock_get_response).status_code = PropertyMock(return_value=404)
        mock_get.return_value = mock_get_response

        # Creating a UserSession instance and calling the login method
        # Expecting a ValueError due to the failed GET request
        user_session = UserSession(username="test_user", password="test_pass")
        with self.assertRaises(ValueError):
            user_session.login()


if __name__ == "__main__":
    unittest.main()
