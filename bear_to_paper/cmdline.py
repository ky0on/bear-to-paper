import argparse
from getpass import getpass
import logging
import sys
import os

from migrator import Migrator


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('documents', nargs='+')
    parser.add_argument('--upload-folder', default='Paper Assets')
    parser.add_argument('--log-level', default='INFO')
    args = parser.parse_args()

    root_logger = logging.getLogger('bear_to_paper')
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.getLevelName(args.log_level))
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(logging.getLevelName(args.log_level))

    access_token = getpass(prompt="Dropbox Access Token: ")

    migrator = Migrator(args.documents, access_token, args.upload_folder)
    migrator.migrate()
