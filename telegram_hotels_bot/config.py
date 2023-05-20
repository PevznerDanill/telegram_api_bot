import os
import sys


TOKEN = ''
api_key_for_currency = ''
rapidAPI_key = ''


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)


def check_config():
    if all(len(config_var) > 0 for config_var in [TOKEN, api_key_for_currency, rapidAPI_key]):
        return True
    return False