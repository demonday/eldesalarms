from dataclasses import dataclass, field
from datetime import date, datetime
import time
from bs4 import BeautifulSoup
from lxml import etree
import requests
from .session import UserSession, BASE_HEADERS
import re
import logging
from progress.bar import Bar
from concurrent.futures import ThreadPoolExecutor


BASE_URL = 'https://gates.eldesalarms.com'
INITIAL_URL = 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}#tabs_tab_users'
USER_DATA_URL = 'https://gates.eldesalarms.com/en/gatesconfig/settings/configuration/ajax/gatesconfig-device-usersdatabase-grid/device_id/{}/GatesconfigDeviceUsersdatabase_page/{}.html?ajax=gatesconfig-device-usersdatabase-grid'  # noqa: E501
LOG_FILE_URL = 'https://gates.eldesalarms.com/en/gatesconfig/settings/getlog/ajax/1/device_id/50550.html?_={}&logstart={}&logend={}'
ADDUSER_PAGE_URL = 'https://gates.eldesalarms.com/en/gatesconfig/settings/users/ajax/1/device_id/{}/tab/1.html?_={}'
ADDUSER_ACTION_ELEMENT = '/html/body/form'
ADDUSER_CONTROLLER_ELEMENT = '//*[@id="GatesconfigDeviceUsersdatabase_output"]/option'
LAST_PAGE_ELEMENT = '/html/body/div[1]/section/div[1]/div/div/div[4]/div/div[2]/div[5]/div/div[2]/ul/li[12]/a'
SYNC_URL = 'https://gates.eldesalarms.com/en/gatesconfig/settings/start/devId/{}.html'  # device_id
SYNC_PROGRESS_URL = 'https://gates.eldesalarms.com/gatesconfig/settings/check?devId={}'  # device_id


@dataclass
class User:
    name: str
    phone: str
    output: str = ''
    app_access: bool = True
    password: str = field(init=False, default=None)


@dataclass
class LogEntry:
    when: datetime
    who: str
    phone: str
    apt_no: str | None


LOG_DATE_FORMAT = '%Y.%m.%d %H:%M:%S'
# 2023.09.23 20:08:56 Opened by user:18TVName(callR:1):0871234567


class DeviceApi:

    class _user_iterator:
        def __init__(self, api):
            self.api = api
            self.cache = []
            self.headers = BASE_HEADERS
            self.headers['Path'] = '/gatesconfig/settings/configuration/device_id/{}'.format(
                self.api.device_id)
            self.headers = self.headers.update(
                {'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}'.format(
                    api.device_id)})

            page = self.api.user_session.get(INITIAL_URL.format(
                self.api.device_id), headers=self.headers)

            # Get the number of pages
            soup = BeautifulSoup(page.content, "html5lib")
            dom = etree.HTML(str(soup))
            last_page_url = dom.xpath(LAST_PAGE_ELEMENT)[
                0].attrib["href"]
            match = re.search(r'/(\d+)\.html$', last_page_url)
            self.max_pages = int(match.group(1) if match else None)
            table = soup.find(
                'table', class_='items table table-striped table-condensed')

            # Get the Users on this page
            tbody = table.find('tbody')
            for i, row in enumerate(tbody.find_all('tr')):
                data = row.find_all('td')
                user = DeviceApi._user_iterator.row_to_user(data)
                self.cache.append(user)
            self.page_no = 2

        @staticmethod
        def row_to_user(data):
            return User(data[0].text.strip(), data[1].text.strip(),
                        data[2].text.strip(), True)

        def __iter__(self):
            return self

        def __next__(self):
            if len(self.cache) != 0:
                return self.cache.pop()
            else:
                if self.page_no <= self.max_pages:
                    page = self.api.user_session.get(USER_DATA_URL.format(
                        self.api.device_id, self.page_no), headers=self.headers)
                    soup = BeautifulSoup(page.content, "html5lib")
                    table = soup.find(
                        'table', class_='items table table-striped table-condensed')
                    tbody = table.find('tbody')
                    for i, row in enumerate(tbody.find_all('tr')):
                        data = row.find_all('td')
                        user = DeviceApi._user_iterator.row_to_user(data)
                        self.cache.append(user)
                    self.page_no += 1
                    # Assumes there is at least one user on the last page
                    return self.cache.pop()
                else:
                    raise StopIteration()

    def __init__(self, user_session: UserSession, device_id: int):
        if not user_session.logged_in and not user_session.login():
            raise ValueError('Session must be logged in to use the api')
        self.user_session = user_session
        self.device_id = device_id

    @property
    def users(self):
        return DeviceApi._user_iterator(self)

    @staticmethod
    def parse_log_line(line: str) -> LogEntry:
        datestr = line[0:19]
        when = datetime.strptime(datestr, LOG_DATE_FORMAT)

        # Extract who
        who_pattern = r'user:(.*?)\(callR'
        who_match = re.search(who_pattern, line)
        if who_match:
            who = who_match.group(1)
        else:
            who = None

        # Using regex to find the number at the beginning of the string
        if who:
            apt_match = re.match(r'^(\d+)', who)
            apt_no = int(apt_match.group(1)) if apt_match else None

        # Extract phone
        phone_pattern = r"\(callR:1\):(\d+)"
        phone_match = re.search(phone_pattern, line)
        if phone_match:
            phone = phone_match.group(1)
        else:
            phone = None

        return LogEntry(when, who, phone, apt_no)

    # https://gates.eldesalarms.com/en/gatesconfig/settings/usersdelete/ajax/1/device_id/50550/number/385/tab/1.html?ajax=gatesconfig-device-usersdatabase-grid
    # ajax: gatesconfig-device-usersdatabase-grid
    # form_data: YII_CSRF_TOKEN=e3ebb2f36832762b9a3159c3d6b54a4d85d2fe74

    def remove_user(self, user: User) -> bool:
        return False

    # Add users to the device, returning the users that were added
    def add_users(self, users: [User]) -> [User]:
        added_users = []
        for user in users:
            try:
                self.add_user(user)
                added_users.append(user)
            except ValueError as e:
                logging.error(
                    f'Error occurred while adding user {user.name}: {e}')
        return added_users

    # https://gates.eldesalarms.com/en/gatesconfig/settings/users/ajax/1/device_id/50550/number/385.html
    def add_user(self, user: User):
        t = datetime.now()
        cache_buster = str(int(time.mktime(t.timetuple())))

        request_url = ADDUSER_PAGE_URL.format(self.device_id, cache_buster)
        headers = BASE_HEADERS
        headers['Path'] = request_url
        headers = headers.update(
            {'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}'.format(
                self.device_id)})

        try:
            # Find the url to post the new user to
            page = self.user_session.get(request_url, headers=BASE_HEADERS)
            soup = BeautifulSoup(page.content, "html5lib")
            dom = etree.HTML(str(soup))
            adduser_post_url = dom.xpath(ADDUSER_ACTION_ELEMENT)[
                0].attrib["action"]

            logging.debug(f'URL to create a new User{adduser_post_url}')
            options = dom.xpath(ADDUSER_CONTROLLER_ELEMENT)

            # Dictionary with option text as key and option value as value.
            adduser_controller_options = {el.text: el.get('value')
                                          for el in options if el is not None and el.text is not None}

            if user.output not in adduser_controller_options:
                raise ValueError(
                    f'Output {user.output} is not a valid output parameter. Valid values are {adduser_controller_options.keys()}')

            params = {'YII_CSRF_TOKEN': self.user_session.token,
                      'GatesconfigDeviceUsersdatabase[phone]': user.phone,
                      'GatesconfigDeviceUsersdatabase[user_name]': user.name,
                      'GatesconfigDeviceUsersdatabase[app]': '1' if user.app_access else '0',
                      'GatesconfigDeviceUsersdatabase[app_password]': user.phone[:-6],
                      'GatesconfigDeviceUsersdatabase[output]': adduser_controller_options[user.output],
                      'GatesconfigDeviceUsersdatabase[schedulerList]': '',
                      'GatesconfigDeviceUsersdatabase[validuntildate]': '',
                      'GatesconfigDeviceUsersdatabase[ring_counter]': ''
                      }

            url = f'{BASE_URL}{adduser_post_url}'
            response = self.user_session.post(url=url, data=params, headers=BASE_HEADERS.update(
                {'Referer': 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}'.format(self.device_id),
                 'Host': 'gates.eldesalarms.com',
                 'Origin': 'https://gates.eldesalarms.com'}))

            if response.status_code != 200:
                raise ValueError(
                    f'Error occurred while adding user {user.name}. Status code {response.status_code}')

        except requests.exceptions.RequestException as e:
            logging.error(f'Error occurred while adding user: {e}')
            raise ValueError(
                'Error occurred while adding user. See log for details.')

    def get_logs(self, start: date, end: date) -> [LogEntry]:

        API_DATE_FMT = '%Y-%m-%d'

        logging.info(f'Getting gate logs from {start} to {end} inclusive.')

        t = datetime.now()
        cache_buster = str(int(time.mktime(t.timetuple())))
        dl_button = '/html/body/div/div/a[2]'

        request_url = LOG_FILE_URL.format(cache_buster, start.strftime(
            API_DATE_FMT), end.strftime(API_DATE_FMT))

        headers = BASE_HEADERS
        headers['Path'] = request_url
        headers = headers.update(
            {'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}'.format(
                self.device_id)})

        # Request the log file link
        page = self.user_session.get(request_url, headers=headers)
        soup = BeautifulSoup(page.content, "html5lib")
        dom = etree.HTML(str(soup))
        download_url = dom.xpath(dl_button)[0].attrib['href']

        # Download the log file from the URL
        log = self.user_session.get(
            f"{BASE_URL}/{download_url}", headers=headers)

        # text looks like
        # 2023.09.23 20:08:56 Opened by user:18TVperson1(call
        # R:1):0871234567
        lines_in = iter(log.text.splitlines())
        log_entries = []
        for line in lines_in:
            log_entries.append(DeviceApi.parse_log_line(line + next(lines_in)))

        return log_entries

    def synchronize(self):
        # Set a timeout value
        timeout = 180  # seconds

        # Using ThreadPoolExecutor to run the function with a timeout
        with ThreadPoolExecutor() as executor:
            future = executor.submit(self.sync_synchronize)
            try:
                result = future.result(timeout)
            except TimeoutError:
                raise TimeoutError(
                    'Unable to complete synchronization within {} seconds. It will continue in the background'.format(timeout))
        return result

    def sync_synchronize(self):
        try:
            sync_response = self.user_session.get(
                SYNC_URL.format(self.device_id), headers=BASE_HEADERS.update(
                    {'Referer': 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}'.format(self.device_id),
                     'Host': 'gates.eldesalarms.com',
                     'Origin': 'https://gates.eldesalarms.com'}))

            if sync_response.status_code not in [200, 302]:
                raise ValueError(
                    'Error occurred while synchronizing. Status code {}'.format(sync_response.status_code))
        except requests.exceptions.RequestException as e:
            logging.error(f'Error occurred while synchronizing: {e}')
            raise ValueError('Error occurred while synchronizing')

        synced = False
        bar = Bar('Synchronizing...', max=100)
        bar.index = 0
        bar.update()
        time.sleep(5)
        progress_response = None
        while not synced:
            try:
                progress_response = self.user_session.get(
                    SYNC_PROGRESS_URL.format(self.device_id), headers=BASE_HEADERS.update(
                        {'Referer': 'https://gates.eldesalarms.com/gatesconfig/settings/configuration/device_id/{}'.format(self.device_id),
                         'Host': 'gates.eldesalarms.com',
                         'Origin': 'https://gates.eldesalarms.com',
                         'X-Requested-With': 'XMLHttpRequest'}))
                # {"percentage":0,"stop":1,"state_string":"Downloading data"}

            except requests.exceptions.RequestException as e:
                logging.debug(
                    f'Error occurred while synchronizing. Sync will still continue. Error: {e}')

            if progress_response is not None:
                percentage_complete = int(
                    progress_response.json()["percentage"])
                bar.index = percentage_complete
                bar.update()
                progress_response = None
                if percentage_complete == 100:
                    bar.finish()
                    synced = True
                else:
                    time.sleep(5)
                    bar.update()
            else:
                time.sleep(5)
                bar.update()

        return True
