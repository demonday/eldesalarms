import unittest
from unittest import mock
from unittest.mock import PropertyMock, patch, Mock
import requests
from eldesalarms.session import UserSession


class TestUserSession(unittest.TestCase):

    @mock.patch('requests.cookies.RequestsCookieJar.get')
    @patch.object(requests.Session, 'get')
    @patch.object(requests.Session, 'post')
    def test_login_successful(self, mock_post, mock_get, mock_cookies_get):

        # Mocking the cookie jar, note the PHPSESSID cookie is different before and after login,
        # and the the cookie used to prevent cross site forgery is the same
        call_count = {}

        def cookie_jar(cookie_name):
            call_count[cookie_name] = call_count.get(cookie_name, 0) + 1
            if cookie_name == 'PHPSESSID':
                if call_count[cookie_name] == 1:
                    return 'PHPSESSID_prelogin'
                else:
                    return 'PHPSESSID_postlogin'
            elif cookie_name == 'YII_CSRF_TOKEN':
                return 'b20935f8678b9fef55f22323db9b1df64f721e44s%3A40%3A%228d16e0d36897636cf43ed9dcf4dae7e164279a4c%22%3B'

        mock_cookies_get.side_effect = cookie_jar

        # Mocking the GET response
        mock_get_response = Mock()
        type(mock_get_response).status_code = PropertyMock(return_value=200)

        # # Mocking the POST response
        mock_post_response = Mock()
        type(mock_post_response).status_code = PropertyMock(return_value=302)

        # Setting up the mocks
        mock_get.return_value = mock_get_response
        mock_post.return_value = mock_post_response

        # Creating a UserSession instance and calling the login method
        user_session = UserSession(username="test_user", password="test_pass")
        login_result = user_session.login()

        # Verifying the login success and token assignment
        self.assertTrue(login_result)
        self.assertEqual(user_session.token,
                         "8d16e0d36897636cf43ed9dcf4dae7e164279a4c")

    @mock.patch('requests.cookies.RequestsCookieJar.get')
    @patch.object(requests.Session, 'get')
    @patch.object(requests.Session, 'post')
    def test_login_failed(self, mock_post, mock_get, mock_cookies_get):

        # Mocking the cookie jar, note the PHPSESSID cookie is different before and after login,
        # and the the cookie used to prevent cross site forgery is the same
        call_count = {}

        def cookie_jar(cookie_name):
            call_count[cookie_name] = call_count.get(cookie_name, 0) + 1
            if cookie_name == 'PHPSESSID':
                if call_count[cookie_name] == 1:
                    return 'PHPSESSID_prelogin'
                else:
                    return 'PHPSESSID_postlogin'
            elif cookie_name == 'YII_CSRF_TOKEN':
                return 'b20935f8678b9fef55f22323db9b1df64f721e44s%3A40%3A%228d16e0d36897636cf43ed9dcf4dae7e164279a4c%22%3B'

        mock_cookies_get.side_effect = cookie_jar

        # Mocking the GET response
        mock_get_response = Mock()
        type(mock_get_response).status_code = PropertyMock(return_value=200)

        # Mocking the POST response (200 is a failure in this case, as it just re-renders the login page)
        mock_post_response = Mock()
        type(mock_post_response).status_code = PropertyMock(return_value=200)

        # Setting up the mocks
        mock_get.return_value = mock_get_response
        mock_post.return_value = mock_post_response

        # Creating a UserSession instance and calling the login method
        user_session = UserSession(username="test_user", password="test_pass")

        with self.assertRaises(ValueError):
            user_session.login()


if __name__ == "__main__":
    unittest.main()
