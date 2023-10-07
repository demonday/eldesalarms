import argparse
from unittest import TestCase, mock
import logging
import sys

import pytest
sys.path.append("src")
from gatecontrol import Stream, setup_logging, main  # noqa:
from eldesalarms.api import User  # noqa:


class TestSetLoggingLevel(TestCase):
    @mock.patch('logging.basicConfig')
    def test_set_logging_level(self, mock_basic_config):
        setup_logging(0)
        mock_basic_config.assert_called_once_with(
            level=logging.WARNING,
            handlers=mock.ANY)
        mock_basic_config.reset_mock()

        setup_logging(1)
        mock_basic_config.assert_called_once_with(
            level=logging.INFO,
            handlers=mock.ANY)
        mock_basic_config.reset_mock()

        setup_logging(2)
        mock_basic_config.assert_called_once_with(
            level=logging.DEBUG,
            handlers=mock.ANY)


class TestStream(TestCase):

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.path.isfile', return_value=True)
    def test_stream_read_mode(self, mock_isfile, mock_exists):
        mock_file = mock.mock_open()
        with mock.patch('builtins.open', mock_file, create=True):
            with Stream("existing_file.txt") as f:
                self.assertIsNotNone(f)

    @mock.patch('os.path.exists', return_value=False)
    def test_stream_write_mode_not_exists(self, mock_isfile):
        mock_file = mock.mock_open()
        with mock.patch('builtins.open', mock_file, create=True):
            with Stream("write_file.txt", write=True) as file:
                self.assertIsNotNone(file)

    @mock.patch('os.path.exists', return_value=True)
    def test_stream_write_mode__already_exists(self, mock_isfile):
        mock_file = mock.mock_open()
        with mock.patch('builtins.open', mock_file, create=True):
            with Stream("write_file.txt", write=True) as file:
                self.assertIsNone(file)

    @mock.patch('os.path.exists', return_value=False)
    def test_stream_invalid_file(self, mock_exists):
        mock_file = mock.mock_open()
        with mock.patch('builtins.open', mock_file, create=True):
            with Stream("non_existent_file.txt") as file:
                self.assertIsNone(file)

    @pytest.mark.skip(reason="Not currently working - ValueError: I/O operation on closed file.")
    def test_stream_stdin(self):
        with Stream("-", write=True) as file:
            self.assertTrue(True)
            self.assertEqual(file, sys.stdout)


class TestMainFunction(TestCase):
    @mock.patch('sys.argv', return_value=['gatecontrol.py', '--username', 'user', '--password', 'pass', '--device',
                '1', '--upload', 'file.txt', '--nosync'])
    @mock.patch('sys.exit')
    @mock.patch('gatecontrol.UserSession', autospec=True)
    @mock.patch('gatecontrol.DeviceApi', autospec=True)
    @mock.patch('builtins.open', new_callable=mock.mock_open, read_data='data')
    @mock.patch('csv.DictReader')
    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_main_upload_with_nosync(self, mock_parse_args, mock_dict_reader, mock_open, mock_device_api, mock_user_session, mock_exit, mock_argv):

        # Set up the return value for parse_args
        args = argparse.Namespace(
            username='user',
            password='pass',
            device='1',
            upload='file.txt',
            nosync=True,
            verbose=0,
            logs=None,
            download=None,
            sync=None,
        )
        mock_parse_args.return_value = args

        mock_user_session_instance = mock_user_session.return_value
        mock_user_session_instance.login.return_value = True
        mock_user_session_instance.logged_in = True

        # Mocking the add_user method on the DeviceApi instance
        mock_device_api_instance = mock_device_api.return_value
        mock_device_api_instance.add_user = mock.MagicMock(return_value=True)

        # Mocking the DictReader to return an iterable with one row
        mock_dict_reader.return_value = iter(
            [{'name': 'John', 'phone': '12345', 'output': 'output', 'app_access': 'True'}])

        # Call main function
        main()

        expected_user = User(name='John', phone='12345',
                             output='output', app_access=True)

        # Verifying that add_user was called once with the expected arguments
        mock_device_api_instance.add_user.assert_called_once_with(
            expected_user)

        # Verifying that synchronize was not called
        mock_device_api_instance.synchronize.assert_not_called()

    @mock.patch('sys.argv', return_value=['gatecontrol.py', '--username', 'user', '--password', 'pass', '--device',
                '1', '--upload', 'file.txt', '--nosync'])
    @mock.patch('sys.exit')
    @mock.patch('gatecontrol.UserSession', autospec=True)
    @mock.patch('gatecontrol.DeviceApi', autospec=True)
    @mock.patch('builtins.open', new_callable=mock.mock_open, read_data='data')
    @mock.patch('csv.DictReader')
    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_main_upload(self, mock_parse_args, mock_dict_reader, mock_open, mock_device_api, mock_user_session, mock_exit, mock_argv):

        # Set up the return value for parse_args
        args = argparse.Namespace(
            username='user',
            password='pass',
            device='1',
            upload='file.txt',
            nosync=False,
            verbose=0,
            logs=None,
            download=None,
            sync=None,
        )
        mock_parse_args.return_value = args

        mock_user_session_instance = mock_user_session.return_value
        mock_user_session_instance.login.return_value = True
        mock_user_session_instance.logged_in = True

        # Mocking the add_user method on the DeviceApi instance
        mock_device_api_instance = mock_device_api.return_value
        mock_device_api_instance.add_user = mock.MagicMock(return_value=True)

        # Mocking the DictReader to return an iterable with one row
        mock_dict_reader.return_value = iter(
            [{'name': 'John', 'phone': '12345', 'output': 'output', 'app_access': 'True'}])

        # Call main function
        main()

        expected_user = User(name='John', phone='12345',
                             output='output', app_access=True)

        # Verifying that add_user was called once with the expected arguments
        mock_device_api_instance.add_user.assert_called_once_with(
            expected_user)

        # Verifying that synchronize was not called
        mock_device_api_instance.synchronize.assert_called_once()
