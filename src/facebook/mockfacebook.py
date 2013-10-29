from kivy import platform
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, StringProperty
from kivy.logger import Logger

import netcheck

class _Request():
    def __init__(self, payload):
        self.payload = payload


class MockFacebook(EventDispatcher):

    __events__ = ('on_open',)

    status = StringProperty('')
    is_open = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        self.is_open = False
        self._pending_request = None

    def post(self, text, callback=None):
        '''Post a new message from the application to the user wall
        '''
        r = _Request(payload=text)
        r.callback = self._wrap_callback(callback)
        r.process = self._process_post
        return self._try_request(r)

    def _process_post(self, req):
        Logger.info(req.payload)
        req.callback(True)

    def image_post(self, description, image_path, callback=None):
        '''Post a photo with a description
        '''
        payload = {'image_path' : image_path,
                   'description' : description}
        r = _Request(payload=payload)
        r.callback = self._wrap_callback(callback)
        r.process = self._process_image_post
        return self._try_request(r)

    def _process_image_post(self, req):
        payload = req.payload
        Logger.info(str(payload))
        req.callback(True)

    def me(self, callback):
        '''Get all the user information.
        '''
        req = _Request(None)
        req.callback = self._wrap_callback(callback)
        req.process = self._process_me
        return self._try_request(req)

    def _process_me(self, req):
        Logger.info('Me callback')
        req.callback(True)

    def _open(self):
        self.status = 'fake login'
        self.is_open=True
        self.dispatch('on_open')

    def _try_request(self, r):
        if self._pending_request is not None:
            Logger.info('request already in progress')
            return False
        elif not netcheck.connection_available():
            self._pending_request = r
            netcheck.ask_connect(self._connection_callback)
            return True
        else:
            Logger.info('doing it now')
        self._pending_request = r
        # this is a pretty robust way to end up processing the request
        self._open()
        return True

    def _wrap_callback(self, callback):
        cp = self._clear_pending
        def cb(*args, **kwargs):
            cp()
            if callback:
                callback(*args, **kwargs)
        return cb

    def _clear_pending(self):
        self._pending_request = None

    def _ask_retry(self):
        self.retry_prompt(self._fail_callback)

    def retry_prompt(self, callback):
        ''' monkey patch here to implement a real prompt'''
        callback(False)

    def set_retry_prompt(self, fn):
        self.retry_prompt = fn

    def _fail(self):
        Logger.info('failed that puppy')
        self._ask_retry()

    def _fail_callback(self, retry):
        if retry and self._pending_request:
            req = self._pending_request
            self._pending_request = None
            self._try_request(req)
        else:
            self._pending_request.callback(False)
            self._clear_pending()

    def _connection_callback(self, connected):
        Logger.info('facebook connect callback - ' + str(connected))
        if connected:
            self._open()
        else:
            self._fail()

    def on_open(self):
        '''ooh! look, hotwiring.
        '''
        if self._pending_request:
            Logger.info('Executing pending_request')
            self._pending_request.process(self._pending_request)
