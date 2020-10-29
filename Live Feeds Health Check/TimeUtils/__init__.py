""" 
Retrieve the timestamp, it will be used to indicated when this script
is executed.

This script requires that `datetime` be installed within the Python
environment you are running this script in.

This file can also be imported as a module and contains the following
functions:

    * getCurrentTimestamp
"""

VERSION = "1.0.0"

from datetime import datetime
import math

def getCurrentTimestamp():
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

def convertFromUtcToDateTime(utcTimestamp):
    """ Return the local date corresponding to the POSIX timestamp """
    return datetime.fromtimestamp(utcTimestamp)