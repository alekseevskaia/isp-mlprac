import argparse
import configparser


_parser = argparse.ArgumentParser()
_parser.add_argument('-c', '--config', default='/etc/mlcourse.conf')

CONFIG = configparser.ConfigParser()
CONFIG.read(_parser.parse_args().config)
