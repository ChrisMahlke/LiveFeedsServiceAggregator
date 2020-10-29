""" 
This module is responsible for returning a status code and a set of details
related to the status code
"""

VERSION = "1.0.0"

def getStatusCode(statusCodeKey: str = "", inputConfig: dict = {}) -> dict:
    """ Returns the status code and messaging  """
    # Legacy code from when the status file was an ini file
    #codeDict = (i for i, e in enumerate(inputConfig) if e["code"] == statusCode)
    #return inputConfig[next(codeDict)]
    return inputConfig.get(statusCodeKey)
