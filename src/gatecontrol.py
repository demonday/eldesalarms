from datetime import datetime
from eldesalarms.session import UserSession
from eldesalarms.api import DeviceApi, User
import logging
import argparse
import sys
import os
import csv
from dataclasses import asdict


def set_logging_level(verbosity):
    if verbosity == 0:
        logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.WARNING)
    elif verbosity == 1:
        logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
    elif verbosity >= 2:
        logging.basicConfig(format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)


class UploadAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        nosync = getattr(namespace, 'nosync', False)
        if nosync is not False and not values:
            parser.error("--nosync can only be used with --upload")
        setattr(namespace, self.dest, values)


class Stream():
    def __init__(self, file_name: str, write: bool = False):
        self.file_name = file_name
        self.mode = 'w' if write else 'r'
        self.file = None

    def __enter__(self):
        if not isinstance(self.file_name, str):
            logging.error("Input to handle_file_input must be a string.")
            return None

        if self.file_name == "-" and self.mode == 'r':
            self.file = sys.stdin
        elif self.file_name == "-" and self.mode == 'w':
            self.file = sys.stdout
        elif self.mode == 'r' and os.path.exists(self.file_name) and os.path.isfile(self.file_name):
            try:
                self.file = open(self.file_name, mode=self.mode)
            except (IOError, PermissionError) as e:
                logging.error(f"Error opening file {self.file_name}: {e}")
                return None
        elif self.mode == 'w' and not os.path.exists(self.file_name):
            try:
                self.file = open(self.file_name, mode=self.mode)
            except (IOError, PermissionError) as e:
                logging.error(f"Error opening file {self.file_name}: {e}")
                return None
        else:
            logging.error(
                f"File {self.file_name} does not exist or is not accessible.")
            return None

        return self.file

    def __exit__(self, exception_type, exception_value, traceback):
        if self.file:
            self.file.close()


def main():

    parser = argparse.ArgumentParser(description="gates.eldesalarms.com data management utility.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("username", type=str,
                        help='username of the account used to login into gates.eldesalarms.com.')
    parser.add_argument("password", type=str,
                        help='password for account used to login into gates.eldesalarms.com.')
    parser.add_argument("device", type=int,
                        help='ID of device to perform the operations on.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--download", metavar='FILE',
                       help='Download all users details to FILE. Use "-" for stdout')
    group.add_argument("--upload", action=UploadAction,
                       help='Upload users details from FILE. Use "-" for stdin', metavar='FILE')

    group.add_argument("--logs", nargs=3, action="append",
                       help='Download Log entries between START and END (inclusive) to FILE. Use "-" for stdout. Dates must be in YYYY-MM-DD',
                       metavar=('FILE', 'START', 'END'))
    group.add_argument("--sync", action="store_true",
                       help='Synchronize data to device.')

    # Add the verbose argument
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase verbosity. Can be specified multiple times.')

    args = parser.parse_args(sys.argv[1:])
    config = vars(args)
    print(config)

    set_logging_level(args.verbose)

    if args.logs:
        date_format = "%Y%m%d"
        file, arg_start, arg_end = args.logs[0]
        start = None
        end = None

        try:
            start = datetime.strptime(arg_start, date_format)
        except Exception:
            parser.error(
                "Unable to parse start date. Format should be YYYYMMDD.")
            exit(1)
        try:
            end = datetime.strptime(arg_end, date_format)
        except Exception:
            parser.error(
                "Unable to parse end date. Format should be YYYYMMDD.")
            exit(1)

    session = UserSession(args.username, args.password)
    if (session.login()):
        api = DeviceApi(session, args.device)
    else:
        logging.error(
            "Unable to login to Eldes Alarms. Please check your credentials")
        exit(1)

    if args.download:
        print("Downloading Users")
        with Stream(args.download, True) as stream:
            csv_writer = csv.writer(stream)
            header = User.__annotations__.keys()
            csv_writer.writerow(header)
            count = 0
            for user in api.users:
                count += 1
                row = asdict(user)
                csv_writer.writerow(row.values())
            print(f'Downloaded {count} Users')

    if args.upload:
        print("Uploading Users")
        added_users: list[User] = []
        with Stream(args.upload) as stream:
            # Using DictReader to read rows into dictionaries
            reader = csv.DictReader(stream)
            for row in reader:
                # Convert app_access string boolean to actual boolean
                row['app_access'] = row['app_access'].lower() == 'true'
                # Initialize User instance with the row data
                user = User(**row)
                if api.add_user(user):
                    added_users.append(user)
            if not args.nosync:
                api.synchronize()

    if args.logs:
        with Stream(file, True) as stream:
            for entry in api.get_logs(start, end):
                stream.write(str(entry))

    if args.sync:
        api.synchronize()

    session.logout()


if __name__ == "__main__":
    main()
