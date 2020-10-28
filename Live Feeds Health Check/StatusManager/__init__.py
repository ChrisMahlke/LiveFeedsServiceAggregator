""" 
This module is responsible for returning a status code and a set of details
related to the status code
"""

VERSION = "1.0.0"


def get_status_code(status_code_key: str = "", input_config=None) -> dict:
    """ Returns the status code and messaging  """
    # Legacy code from when the status file was an ini file
    if input_config is None:
        input_config = {}
    return input_config.get(status_code_key)