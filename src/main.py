from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty
from kivy.logger import Logger
from kivy import platform

import netcheck
from facebook import Facebook

FACEBOOK_APP_ID = '201598793273306'



class ModalCtl:
    ''' just a container for keeping track of modals and implementing
    user prompts.'''
    def ask_connect(self, tried_connect_callback):
        Logger.info('Opening net connect prompt')
        text = ('You need internet access to do that.  Do you '
                'want to go to settings to try connecting?')
        content = AskUser(text=text,
                          action_name='Settings',
                          callback=tried_connect_callback,
                          auto_dismiss=False)
        p = Popup(title = 'Network Unavailable',
                  content = content,
                  size_hint=(0.8, 0.4),
                  pos_hint={'x':0.1, 'y': 0.35})
        modal_ctl.modal = p
        p.open()

    def ask_retry_facebook(self, retry_purchase_callback):
        Logger.info('Facebook Failed')
        text = ('Zuckerberg is on vacation in Monaco.  Would'
                ' you like to retry?')
        content = AskUser(text=text,
                          action_name='Retry',
                          callback=retry_purchase_callback,
                          auto_dismiss=False)
        p = Popup(title = 'Facebook Error',
                  content = content,
                  size_hint=(0.8, 0.4),
                  pos_hint={'x':0.1, 'y': 0.35})
        modal_ctl.modal = p
        p.open() 


class AskUser(RelativeLayout):
    ''' Callback(bool) if user wants to do something'''
    action_name = StringProperty()
    cancel_name = StringProperty()
    text = StringProperty()
    
    def __init__(self, 
                 action_name='Okay', 
                 cancel_name='Cancel', 
                 text='Are you Sure?',
                 callback=None, # Why would you do this?
                 *args, **kwargs):
        self.action_name = action_name
        self.cancel_name = cancel_name
        self._callback = callback
        self.text = text
        modal_ctl.modal = self
        super(AskUser, self).__init__(*args, **kwargs)

    def answer(self, yesno):
        ''' Callbacks in prompts that open prompts lead to errant clicks'''
        modal_ctl.modal.dismiss()
        if self._callback:
            def delay_me(*args):
                self._callback(yesno)
            Clock.schedule_once(delay_me, 0.1)


class FacebookUI(BoxLayout):
    ''' Seems like there was a bug in the kv that wouldn't bind on 
    app.facebook.status, but only on post_status '''

    status_text = StringProperty()
    def __init__(self, **kwargs):
        super(FacebookUI, self).__init__(**kwargs)
        app.bind(facebook=self.hook_fb)
    
    def hook_fb(self, app, fb):
        fb.bind(status=self.on_status)
        app.bind(post_status=self.on_status)
        
    def on_status(self, instance, status):
        self.status_text = \
        'Facebook Status: [b]{}[/b]\nMessage: [b]{}[/b]'.format(
            app.facebook.status, 
            app.post_status)


class FacebookApp(App):

    post_status = StringProperty('-')
    user_infos = StringProperty('-')
    facebook = ObjectProperty()

    def build(self):
        global app
        app = self
        return FacebookUI()

    def on_start(self):
        self.facebook = Facebook(FACEBOOK_APP_ID,
                                 permissions=['publish_actions', 'basic_info'])
        global modal_ctl
        modal_ctl = ModalCtl()
        netcheck.set_prompt(modal_ctl.ask_connect)
        self.facebook.set_retry_prompt(modal_ctl.ask_retry_facebook)

    def fb_me(self):
        def callback(success, user=None, response=None, *args):
            if not success:
                return
            '''since we're using the JNIus proxy's API here,
            we have to test if we're on Android to avoid implementing
            a mock user class with the verbose Java user interface'''
            if platform() == 'android' and response.getError():
                Logger.info(response.getError().getErrorMessage())
            if platform() == 'android' and not response.getError():
                infos = []
                infos.append('Name: {}'.format(user.getName()))
                infos.append('FirstName: {}'.format(user.getFirstName()))
                infos.append('MiddleName: {}'.format(user.getMiddleName()))
                infos.append('LastName: {}'.format(user.getLastName()))
                infos.append('Link: {}'.format(user.getLink()))
                infos.append('Username: {}'.format(user.getUsername()))
                infos.append('Birthday: {}'.format(user.getBirthday()))
                location = user.getLocation()
                if location:
                    infos.append('Country: {}'.format(location.getCountry()))
                    infos.append('City: {}'.format(location.getCity()))
                    infos.append('State: {}'.format(location.getState()))
                    infos.append('Zip: {}'.format(location.getZip()))
                    infos.append('Latitude: {}'.format(location.getLatitude()))
                    infos.append('Longitude: {}'.format(location.getLongitude()))
                else:
                    infos.append('No location available')
            else:
                infos = ['ha', 'ha', 'wish', 'this', 'was', 'real']
            self.user_infos = '\n'.join(infos)
        self.facebook.me(callback)

    def fb_post(self, text):
        def callback(success, response=None, *args):
            if platform() == 'android' and response.getError():
                Logger.info(response.getError().getErrorMessage())
            Logger.info(str(success))
            for a in args:
                Logger.info(str(a))
            if success:
                from time import time
                self.post_status = 'message posted at {}'.format(time())
        self.facebook.post(text, callback=callback)

    def fb_image_post(self, description, image_path):
        def callback(success, *args):
            Logger.info(str(success))
            for a in args:
                Logger.info(str(a))
            if success:
                from time import time
                self.post_status = 'message posted at {}'.format(time())
        self.facebook.image_post(description, image_path, callback=callback)

    def on_pause(self):
        return True


if __name__ == '__main__':
    FacebookApp().run()

