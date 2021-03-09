"""
Print User and Install information to stdout

This script allows prints to stdout information about the authenticated
user and install information about the environment in which the script is
being executed.

This script requires that datetime and sys be installed within the Python
environment you are running this script in.


"""
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

    def __init__(self, user, install_info):
        """

        :param user: User information
        :param install_info: Install info
        """
        self.user = user
        self.install_info = install_info

    def greeting(self):
        """
        Print to stdout a welcome message
        :return: None
        """
        print(datetime.datetime.now().strftime("%A, %B %d, %I:%M %p"))
        print("Welcome " + self.user.firstName + " " + self.user.lastName)
        print(self.install_info["ProductName"] + " " + self.install_info["Version"] + " (" + self.install_info[
            "LicenseLevel"] + ")")
        print("Python version " + sys.version)
