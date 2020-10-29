"""Print User and Install information to stdout

This script allows prints to stdout information about the authenticated
user and install information about the envirment in which the script is
being executed.

This script requires that `datetime` and `sys` be installed within the Python
environment you are running this script in.

This file can also be imported as a module and contains the following
functions:

    * greeting
"""

VERSION = "1.0.0"

import datetime
import sys

class User:
    """ 
    Prints to stdout information about the current signed in user and the 
    Python and ArcGIS environment

    Attributes
    ----------

    Methods
    ----------
    greeting(self)

    """

    def __init__(self, user, installInfo):
        """
        Parameters
        ----------
        user : str
            The user
        installInfo : str
            Install information
        """
        self.user = user
        self.installInfo = installInfo

    def greeting(self):
        """ Print to stdout a welcome message """
        print(datetime.datetime.now().strftime("%A, %B %d, %I:%M %p"))
        print("Welcome " + self.user.firstName + " " + self.user.lastName)
        print(self.installInfo["ProductName"] + " " + self.installInfo["Version"] + " (" + self.installInfo["LicenseLevel"] + ")")
        print("Python version " + sys.version)
