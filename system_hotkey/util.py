# Copyright (c) 2015, tim
# All rights reserved.

import _thread as thread
import threading
from queue import Queue
import queue
from functools import wraps


def unique_int(values):
    last = 0
    for num in values:
        if last not in values:
            break
        else:
            last += 1
    return last


class ExceptionSerializer:
    def __init__(self):
        self.queue = queue.Queue()

    def catch_and_raise(self, func, timeout=0.5):
        self.wait_event(func, timeout)
        self._check_for_errors()

    def mark_done(self, function):
        self.init_wrap(function)

        @wraps(function)
        def decorator(*args, **kwargs):
            self.clear_event(function)
            try:
                results = function(*args, **kwargs)
            except Exception as err:
                self.queue.put(err)
            else:
                return results
            finally:
                self.set_event(function)

        return decorator

    def put(self, x):
        self.queue.put(x)

    def init_wrap(self, func):
        name = self._make_event_name(func)
        event = threading.Event()
        setattr(self, name, event)

    def _check_for_errors(self):
        try:
            error = self.queue.get(block=False)
        except queue.Empty:
            pass
        else:
            raise error

    @staticmethod
    def _make_event_name(func):
        return '_event_' + func.__name__

    def get_event(self, func):
        return getattr(self, self._make_event_name(func))

    def set_event(self, func):
        self.get_event(func).set()

    def clear_event(self, func):
        self.get_event(func).clear()

    def wait_event(self, func, *args):
        self.get_event(func).wait(*args)


class CallSerializer():
    def __init__(self):
        self.queue = Queue()
        thread.start_new_thread(self.call_functions, (),)
        self.bug_catcher = ExceptionSerializer()

    def call_functions(self):
        while 1:
            func, args, kwargs = self.queue.get(block=True)
            func(*args, **kwargs)

    def serialize_call(self, timeout=0.5):
        def state(function):
            @wraps(function)
            def decorator(*args, **kwargs):
                mark_func = self.bug_catcher.mark_done(function)
                self.queue.put((mark_func, args, kwargs))
                self.bug_catcher.catch_and_raise(function, timeout)
            return decorator
        return state
