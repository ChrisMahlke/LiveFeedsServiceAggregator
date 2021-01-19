""" 
Retrieve the timestamp, it will be used to indicated when this script
is executed.

This script requires that `datetime` be installed within the Python
environment you are running this script in.

This file can also be imported as a module and contains the following
functions:

    * getCurrentTimestamp
"""
from datetime import datetime, timedelta
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
    """
    Return the local date corresponding to the POSIX timestamp
    :param utc_timestamp:
    :return:
    """
    return datetime.fromtimestamp(utc_timestamp)


def is_now_excluded(excluded_time_ranges=None, excluded_days=None, excluded_dates=None, ct=None):
    """
    Compare the current timestamp of the run to any or all of the input exclusion parameters.

    :param excluded_time_ranges: A comma separated list of string representing time rangers in the format of
    hh:mm AM/PM - hh:mm AM/PM
    :param excluded_days: A comma separated list of strings each representing a day of the week in integer format
    (e.g. 0,1,3)
    :param excluded_dates: A comma separated list of strings, each representing a specific mm/dd/yyyy
    :param ct: The current timestamp this script is run

    :return: A boolean value indicating whether or not the current timestamp is within the range of ANY of the input
    time parameters
    """

    # check if the current time range is excluded
    if excluded_time_ranges:
        excluded_time_ranges_list = excluded_time_ranges.split(",")
        if excluded_time_ranges_list:
            time_now = datetime.strptime(datetime.strftime(datetime.now(), "%I:%M%p"), "%I:%M%p")
            for excluded_time_range in excluded_time_ranges_list:
                ts, te = excluded_time_range.split(" - ")
                time_start = datetime.strptime(ts, "%I:%M%p")
                time_end = datetime.strptime(te, "%I:%M%p")

                if _is_now_in_time_range(time_start, time_end, time_now):
                    return True

    # iterate through the days of the week to determine if today is excluded
    today = _get_day_of_week(ct)
    if excluded_days:
        # get a list of the excluded days
        excluded_days_list = excluded_days.split(",")
        # check if there are any values in the list
        if excluded_days_list:
            # iterate through the list
            for excluded_day in excluded_days_list:
                if int(today) == int(excluded_day):
                    return True

    # iterate through the excluded dates (if any) and check to see if today is to be excluded
    # if today is excluded then we return True
    if excluded_dates:
        excluded_dates_list = excluded_dates.split(",")
        for excluded_date in excluded_dates_list:
            excluded_date_string = datetime.strptime(excluded_date, "%m/%d/%Y")
            if (datetime.today() - excluded_date_string).days == 0:
                return True

    return False


def is_event_in_time_range(time_to_check=None, time_limit=None) -> bool:
    """
    Check the event time to see if it falls within the range
    :param time_to_check:
    :param time_limit: Time range in days "ago"
    :return:
    """
    time_now = datetime.now() - timedelta(days=0)
    target_time = datetime.fromtimestamp(time_to_check)
    diff = time_now - target_time
    if diff.days <= int(time_limit):
        return True
    return False


def _is_now_in_time_range(start_time=None, end_time=None, now_time=None):
    """
    Determine if the input time is within (inclusive) of the start and end times
    :param start_time:
    :param end_time:
    :param now_time:
    :return:
    """
    if start_time < end_time:
        return now_time >= start_time and now_time <= end_time
    else:  # Over midnight
        return now_time >= start_time or now_time <= end_time


def _get_day_of_week(utc_timestamp=None):
    """
    Return the day of the week
    :param utc_timestamp:
    :return: String representation of the day of the week where Sunday is the
    first day "0" and Saturday is the last day "6".
    """
    return datetime.fromtimestamp(utc_timestamp).strftime("%w")
