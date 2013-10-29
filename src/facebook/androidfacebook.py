from kivy.properties import StringProperty, BooleanProperty
from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.app import App
from jnius import autoclass, PythonJavaClass, java_method, cast
from android import activity
from android.runnable import run_on_ui_thread
import os

import netcheck
import toast

context = autoclass('org.renpy.android.PythonActivity').mActivity
Arrays = autoclass('java.util.Arrays')
Session = autoclass('com.facebook.Session')
SessionBuilder = autoclass('com.facebook.Session$Builder')
SessionOpenRequest = autoclass('com.facebook.Session$OpenRequest')
SessionNewPermissionsRequest = autoclass('com.facebook.Session$NewPermissionsRequest')
Request = autoclass('com.facebook.Request')


class _FacebookStatusCallback(PythonJavaClass):
    __javainterfaces__ = ['com.facebook.Session$StatusCallback']
    __javacontext__ = 'app'

    def __init__(self, fb):
        self.fb = fb
        super(_FacebookStatusCallback, self).__init__()

    @java_method('(Lcom/facebook/Session;Lcom/facebook/SessionState;Ljava/lang/Exception;)V')
    def call(self, session, state, exception):
        self.fb.status = state.toString()
        self.fb._update_state()


class _FacebookRequestCallback(PythonJavaClass):
    __javainterfaces__ = ['com.facebook.Request$Callback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_FacebookRequestCallback, self).__init__()

    @java_method('(Lcom/facebook/Response;)V')
    def onCompleted(self, response):
        success = response.getError() is None
        self.callback(success, response)


class _FacebookGraphUserCallback(PythonJavaClass):

    __javainterfaces__ = ['com.facebook.Request$GraphUserCallback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        self.callback = callback
        super(_FacebookGraphUserCallback, self).__init__()

    @java_method('(Lcom/facebook/model/GraphUser;Lcom/facebook/Response;)V')
    def onCompleted(self, user, response):
        success = response.getError() is None
        self.callback(success, user, response)


class _Request():
    ''' We need one of these to allow on-demand creation of sessions
    inependently of running the request. Package up API calls and 
    process them later.  Also good place to put refs '''
    def __init__(self, payload):
        self.payload = payload


class AndroidFacebook(EventDispatcher):
    '''Facebook connector object. Permissions can be found at:

        https://developers.facebook.com/docs/reference/fql/permissions/
    '''

    status = StringProperty('')
    '''Return the current status of the facebook session.
    '''

    is_open = BooleanProperty(False)
    '''True if the session is ready to use.
    '''

    __events__ = ('on_open', 'on_closed')

    def __init__(self, app_id, permissions=['basic_info'], toasty=True):
        super(AndroidFacebook, self).__init__()
        self._app_id = app_id
        self._permissions = permissions
        self.toasty = toasty
        self._pending_request = None

        activity.bind(on_activity_result=self._on_activity_result)
        self._session_callback = _FacebookStatusCallback(self)
        self._session = None

    def on_closed(self, error):
        '''Fired when the Facebook session has been closed. An additionnal
        `error` message might be passed.
        '''
        pass

    def post(self, text, callback=None):
        '''Post a new message from the application to the user wall
        '''
        r = _Request(payload=text)
        r.callback = self._wrap_callback(callback)
        r.process = self._process_post
        return self._try_request(r)

    def _process_post(self, req):
        req.j_callback = _FacebookRequestCallback(req.callback)
        req.req = Request.newStatusUpdateRequest(
                self._session, req.payload, req.j_callback)

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
        File = autoclass('java.io.File')
        image_file = File(os.path.abspath(payload['image_path']))
        req.j_callback = _FacebookRequestCallback(req.callback)
        r = Request.newUploadPhotoRequest(
            self._session, image_file, req.j_callback)
        params = r.getParameters()
        params.putString("message", payload['description']);
        req.req = r 

    def me(self, callback):
        '''Get all the user information.
        '''
        req = _Request(None)
        req.callback = self._wrap_callback(callback)
        req.process = self._process_me
        return self._try_request(req)

    def _process_me(self, req):
        req.j_callback =  _FacebookGraphUserCallback(req.callback)
        req.req = Request.newMeRequest(
            self._session, req.j_callback)

    def _try_request(self, r):
        if self._pending_request is not None:
            self._toast('request already in progress')
            return False
        elif not netcheck.connection_available():
            self._pending_request = r
            netcheck.ask_connect(self._connection_callback)
            return True
        elif not self.is_open:
            self._toast('will facebook shortly')
        else:
            self._toast('facebooking')
        self._pending_request = r
        # this is a pretty robust way to end up processing the request
        self._open()
        return True

    #
    # private
    #

    def _update_state(self):
        status = self.status
        if status == 'OPENED' or status == 'OPENED_TOKEN_UPDATED':
            self.is_open = True
            self.dispatch('on_open')
            App.get_running_app().bind(on_stop=self._close)
        elif status == 'CLOSED' or status == 'CLOSED_LOGIN_FAILED':
            self.is_open = False
            if self._pending_request:
                self._fail()
            
    def _on_activity_result(self, requestCode, resultCode, data):
        # When the activity got a result, pass it to facebook for processing.
        if self._session is not None:
            result =  self._session.onActivityResult(
                cast('android.app.Activity', context),
                requestCode, resultCode, data)
            # need to find out if this is the desired Boolean to stop
            # processing the activity by other activity listeners
            Logger.info(str(result))
            return result

    def _open(self):
        '''Open a facebook connection.
        When the session is opened, the event `on_open` will be fired.
        '''
        if self._session is None:
            self._session = Session.getActiveSession()
        if self._session and self._session.isOpened():
            self.dispatch('on_open')
        else:
            builder = SessionBuilder(context)
            self._session = builder.setApplicationId(self._app_id).build()
            Session.setActiveSession(self._session)
            self._session.addCallback(self._session_callback)

            self.req = SessionOpenRequest(cast('android.app.Activity', context))
            self.req.setPermissions(Arrays.asList(*self._permissions))
            # facebook java will warn if you're using only write permissions,
            # but works nontheless
            self._session.openForPublish(self.req)

    @run_on_ui_thread
    def on_open(self):
        '''Fired when the Facebook session is opened and ready to use.
        '''
        # Facebook said the asynchronous request must be run in the ui thread.
        # ref: https://developers.facebook.com/docs/reference/androidsdk/ayncrequest/
        if self._pending_request:
            Logger.info('Executing pending_request')
            self._pending_request.process(self._pending_request)
            self._pending_request.req.executeAsync()

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
        Logger.info('failed')
        if self._pending_request:
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

    def _close(self, *args):
        if self._session and self._session.isOpened():
            self._session.close()

    def _toast(self, text, length_long=False):
        if self.toasty:
            toast.toast(text, length_long)
