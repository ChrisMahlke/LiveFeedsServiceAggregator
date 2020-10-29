""" 
Retrieve the timestamp, it will be used to indicated when this script
is executed.

This script requires that `datetime` be installed within the Python
environment you are running this script in.

This file can also be imported as a module and contains the following
functions:

    * getCurrentTimestamp
"""
from datetime import datetime
import math

VERSION = "1.0.0"


def get_current_time_and_date():
    """ 
    Get the current date and time (this wil be included at the root level
    of the JSON data model. The datetime module supplies classes for
    manipulating dates and times
    """

    # now() returns the current local date and time.
    ct = datetime.now()
    # Return POSIX timestamp corresponding to the datetime instance. The
    # return value is a float similar to that returned by time.time().
    ct_timestamp = datetime.timestamp(ct)
    # remove the milliseconds
    dt = ct.replace(microsecond=0)
    # Return POSIX timestamp as float
    timestamp = datetime.timestamp(dt)
    # Construct a datetime from a POSIX timestamp
    dt_object = datetime.fromtimestamp(ct_timestamp)

    return {
        "timestamp": math.trunc(timestamp),
        "datetimeObj": dt_object
    }


def convert_from_utc_to_datetime(utc_timestamp):
    """ Return the local date corresponding to the POSIX timestamp """
    return datetime.fromtimestamp(utc_timestamp)
