from http import HTTPStatus
import urllib.request
import urllib.parse
import urllib.error
import requests
import ssl
import re
import logging


LOGIN_URL = "https://gates.eldesalarms.com/en/user/login.html"
LOGOUT_URL = "https://gates.eldesalarms.com/user/logout"

BASE_HEADERS = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',  # noqa: E501
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Connection': 'keep-alive',
                'Host': 'gates.eldesalarms.com',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'Method': 'GET',
                'Path': '/en/user/login.html',
                'Protocol': 'HTTP/1.1'}


class UserSession(requests.Session):

    # default constructor
    def __init__(self, username: str, password: str):
        super().__init__()
        self.logged_in = False
        self.username = username
        self.password = password

    def login(self) -> bool:

        # Ignore SSL certificate errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        try:
            super().get(LOGIN_URL, headers=BASE_HEADERS)
        except requests.exceptions.RequestException as e:
            logging.error(f'Error occurred while requesting login page: {e}')
            raise ValueError('Could not connect to Eldes Alarms')

        pre_login_session_id = self.cookies.get("PHPSESSID")
        logging.debug(f'Session Id (Pre-Login): {pre_login_session_id}')

        # Extracting the last parameter of the token and remove the double quotes,
        # to yield the YII_CSRF_TOKEN parameter required to login properly

        match = re.search(
            r'"([^"]+)"', urllib.parse.unquote(self.cookies.get("YII_CSRF_TOKEN")))
        self.token = match.group(1) if match else None

        params = {'YII_CSRF_TOKEN': self.token,
                  'UserLogin[username]': self.username, 'UserLogin[password]': self.password}
        try:
            logged_in_page = super().post(
                url=LOGIN_URL, data=params, headers=BASE_HEADERS.update({'Referer': LOGIN_URL, 'Host': 'gates.eldesalarms.com',
                                                                         'Origin': 'https://gates.eldesalarms.com'}))
            logging.debug(
                f'Session Id (Post-Login): {self.cookies.get("PHPSESSID")}')

            # If successfully logged-in, we get a 200 response code, and a new session id
            if logged_in_page.status_code == HTTPStatus.OK and self.cookies.get("PHPSESSID") != pre_login_session_id:
                self.logged_in = True
            else:
                logging.error(
                    f'Error occurred while logging in. Status code {logged_in_page.status_code}')
                raise ValueError(
                    f'Unable to login to Eldes Alarms with username {self.username}. Please check your credentials')

        except requests.exceptions.RequestException as e:
            logging.error(f'Error occurred while logging in: {e}')
            raise ValueError('Error occurred while logging in')

        return self.logged_in

    def logout(self):
        if (self.logged_in):
            try:
                super().get(LOGOUT_URL, headers=BASE_HEADERS)
                self.logged_in = False
            except requests.exceptions.RequestException as e:
                logging.error(f'Error occurred while logging out: {e}')
                raise ValueError('Error occurred while logging out.')
        else:
            logging.error(
                'Cannot log out because this UserSession is not logged in.')
            raise ValueError('Not logged in.')
