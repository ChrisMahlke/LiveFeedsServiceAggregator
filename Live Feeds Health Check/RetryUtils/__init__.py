""" """
from datetime import datetime, timedelta
from typing import Optional, Tuple, TypeVar, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

import http.client
import socket

# Python is a dynamically typed language. This means that the Python
# interpreter does type checking only as code runs, and that the type of a
# variable is allowed to change over its lifetime.
#
# A type variable is a special variable that can take on any type, depending
# on the situation.  Let’s create a type variable that will effectively 
# encapsulate the behavior of a Session object:
T = TypeVar("T", bound=requests.Session)

retry_output = []


def _patch_send():
    """ Debugging: Represents one transaction with an HTTP server """
    old_send = http.client.HTTPConnection.send

    def new_send(self, data):
        print(data.decode('utf-8'))
        return old_send(self, data)

    http.client.HTTPConnection.send = new_send


class TimeoutSession(requests.Session):
    """A session that has a timeout for all of its requests."""

    # Union allows a value to be any one of a given set of types, and type
    # check correctly for any of them.
    def __init__(self, timeout: Union[int, timedelta] = 5):
        """
        Args:
            timeout: Time that requests will wait to receive the first
                     response bytes (not the whole time) from the server.
                     An int in seconds or a timedelta object.
        """
        # super() gives you access to methods in a superclass from the subclass
        # that inherits from it.  All methods that are called with super() need
        # to have a call to their superclass’s version of that method. This
        # means that you will need to add super().__init__() to the .__init__()
        # methods
        super().__init__()
        # set the timeout
        self.timeout = timeout if isinstance(timeout, int) else timeout.seconds
        print(f"TimeoutSession")

    # override the request method
    # *args and **kwargs allow you to pass multiple arguments or keyword
    # arguments to a function.
    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        # output request calls for debugging
        print(f"TimeoutSession: request: {url}")
        # _patch_send()
        return super().request(method, url, *args, **kwargs)


class RetrySession(TimeoutSession):
    """A session that has a timeout and a `raises_for_status`
     for all of its requests.

     raise_for_status: will raise an HTTPError if the HTTP request returned an
     unsuccessful status code.
    """

    def __init__(self, timeout: Union[int, timedelta] = 5):
        super().__init__(timeout)
        self.hooks["response"] = lambda r, *args, **kwargs: r.raise_for_status()


class CallbackRetry(Retry):
    """
    Subclass Retry
    Each retry attempt will create a new Retry object with updated values, so
    they can be safely reused.
    """
    def __init__(self, *args, **kwargs):
        self._callback = kwargs.pop('callback', None)
        self._id = kwargs.pop('id', None)
        self._counter = kwargs.pop('counter', None)
        self._start_time = kwargs.pop('start_time', None)
        super(CallbackRetry, self).__init__(*args, **kwargs)

    def new(self, **kw):
        # pass along the subclass additional information when creating
        # a new instance.
        kw['callback'] = self._callback
        kw['id'] = self._id
        kw['counter'] = self._counter
        kw['start_time'] = self._start_time
        return super(CallbackRetry, self).new(**kw)

    def increment(self, method, url, *args, **kwargs):
        self._counter += 1
        if self._callback:
            try:
                self._callback(url, self._id, self._counter, self._start_time)
            except Exception:
                print("Callback raised an exception, ignoring")
        return super(CallbackRetry, self).increment(method, url, *args, **kwargs)


def retry_callback(url, item_id, counter, start_time):
    print(f"\n--- Callback invoked {item_id} ---")
    print(f"url: {url}")
    print(f"counter: {counter}")
    ct = datetime.now()
    ct_timestamp = datetime.timestamp(ct)
    dt_object = datetime.fromtimestamp(ct_timestamp)
    print(f"{dt_object}\n")

    retry_output.append({
        "id": item_id,
        "retryCount": counter
    })


def get_retry_output():
    return retry_output


def retry(
        session: Optional[T] = None,
        retries: int = 3,
        backoff_factor: float = 1,
        status_to_retry: Tuple[int, ...] = (500, 502, 504),
        prefixes: Tuple[str, ...] = ("http://", "https://"),
        **kwargs
) -> Union[T, RetrySession]:
    """
    Configures the passed-in session to retry on failed requests
    due to connection errors, specific HTTP response codes and
    30X redirections.

    Args:
        session: A session to allow to retry. None creates a new Session.
                 If necessary, Optional[t] is added for function and method
                 annotations if a default value equal to None is set.
        retries: The number of maximum retries before raising an
                 exception.
        backoff_factor: A factor used to compute the waiting time between
                        retries.
                        See :arg:`urllib3.util.retry.Retry.backoff_factor`.
        status_to_retry: A tuple of status codes that trigger the reply
                         behaviour.
        prefixes: A tuple of URL prefixes that this retry configuration
                  affects. By default, ``https`` and ``https``.
        **kwargs: Extra arguments that are passed to
                  :class:`urllib3.util.retry.Retry`.

    Returns:
        A session object with the retry setup.
    """
    item_id = kwargs.pop("id", False)
    timeout = kwargs.pop("timeout", False)

    session = session or RetrySession()

    ct = datetime.now()
    ct_timestamp = datetime.timestamp(ct)
    dt_object = datetime.fromtimestamp(ct_timestamp)
    print(f"Query time: {dt_object}")
    print(f"--- parameters (RetryUtils) ---")
    print(f"retry: {retries}")
    print(f"timeout: {timeout}\n")

    # Retry too in non-idempotent methods like POST
    kwargs.setdefault("method_whitelist", False)
    # Subclass Retry
    max_retry_count = CallbackRetry(total=retries,
                                    status_forcelist=[408, 500, 502, 503, 504],
                                    callback=retry_callback,
                                    id=item_id,
                                    counter=0,
                                    start_time=ct)
    for prefix in prefixes:
        # The second parameter of mount accepts a Transport Adaptor object.
        # Transport adapters provide a mechanism to define interaction methods for an “HTTP” service. They allow you to
        # fully mock a web service to fit your needs.
        #
        # And the HTTP Adapter provides a general-case interface for Requests sessions to contact HTTP and HTTPS urls by
        # implementing the Transport Adapter interface
        #
        # NOTE: max_retries is the maximum number of retries each connection should attempt. This applies only to failed
        # DNS lookups, socket connections and connection timeouts, never to requests where data has made it to the
        # server. By default, Requests does not retry failed connections. For more granular control over the conditions
        # under which we retry a request, I import urllib3’s Retry class and pass that instead (as recommended by the
        # documentation for the HTTPAdapter).
        session.mount(prefix, HTTPAdapter(max_retries=max_retry_count))
    return session
