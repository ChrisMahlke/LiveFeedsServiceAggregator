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


def is_now_excluded(excluded_dates, excluded_days=None, excluded_time_ranges=None, ct=None):
    """ Check if the current time is excluded from the run """
    exclude = False
    # iterate through the excluded dates (if any)
    if len(excluded_dates) > 0:
        excluded_dates_list = excluded_dates.split(",")
        for excluded_date in excluded_dates_list:
            excluded_date_string = datetime.strptime(excluded_date, "%m/%d/%Y")
            if (datetime.today() - excluded_date_string).days == 0:
                return True

    # iterate through the days of the week to determine if today is excluded
    today = _get_day_of_week(ct)
    if len(excluded_days) > 0:
        # get a list of the excluded days
        excluded_days_list = excluded_days.split(",")
        # check if there are any values in the list
        if len(excluded_days_list) > 0:
            # iterate through the list
            for excluded_day in excluded_days_list:
                if int(today) == int(excluded_day):
                    return True

    # check if the current time range is excluded
    if len(excluded_time_ranges) > 0:
        excluded_time_ranges_list = excluded_time_ranges.split(",")
        if len(excluded_time_ranges_list) > 0:
            for excluded_time_range in excluded_time_ranges_list:
                # TODO
                time_now = datetime.strftime(datetime.now(), "%I:%M%p")
                tn = datetime.strptime(time_now, "%I:%M%p")

                time_start = excluded_time_range
                ts = datetime.strptime(time_start.split(" - ")[0], "%I:%M%p")

                time_end = excluded_time_range
                te = datetime.strptime(time_end.split(" - ")[1], "%I:%M%p")

                if _is_now_in_time_range(ts, te, tn):
                    return True
    # if we reach this point, we are not excluding this timeframe
    return exclude


def _get_day_of_week(utc_timestamp=None):
    """
    Return the day of the week
    :param utc_timestamp:
    :return:
    """
    return datetime.fromtimestamp(utc_timestamp).strftime("%w")


def _is_now_in_time_range(start_time, end_time, now_time):
    """
    Determine if the input time is within (inclusive) of the start and end times
    :param startTime:
    :param endTime:
    :param nowTime:
    :return:
    """
    if start_time < end_time:
        return now_time >= start_time and now_time <= end_time
    else:  # Over midnight
        return now_time >= start_time or now_time <= end_time
