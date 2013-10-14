Kivy + Facebook SDK
===================

#### Features:
* post to timeline
* image post with description
* uses toasts and netcheck to make UX better

#### Install
Pre-built application in ```/bin```
adb install -r /bin/FacebookExample-0.1-debug-unaligned.apk

#### Build

The documentation for creating a Facebook application and several other can be found here:

    http://kivy.org/planet/2013/08/using-facebook-sdk-with-python-for-android-kivy/

This example works only on Android.  There is a mock module to aid with development.

Create debug hash key (default debug key password is `android`)::

    # with shell script
    ./base64sig.sh
    # will get debug key.  password is android
    # to get production sig:
    ./base64sig.sh mykestore.keystore

    # manually
    keytool -exportcert -alias androiddebugkey -keystore \ 
        ~/.android/debug.keystore  | openssl sha1 -binary | openssl base64

* Make Facebook SDK project data
cd ~/my/facebook/dir/../facebook
android update project -p .

Copy the browser.sh to a P4A dist then run:
```facebook.sh my/path/to/src/```
If it doesn't work, edit facebook.sh to configure P4A to build this.  Need PyJNIus in your dist. 

#### Issues:

* W/fb4a:fb:OrcaServiceQueue(28514): com.facebook.orca.protocol.base.ApiException:
  The proxied app is not already installed.

  -> ?, doesn't seem dangerous.

* In FB SDK 3.5:
You need to modify the java or else crash every time you make a session
change 821-2 in AuthorizationClient.java to:

    ""+intent.getIntExtra(NativeProtocol.EXTRA_PROTOCOL_VERSION, 0));
    //intent.getStringExtra(NativeProtocol.EXTRA_PROTOCOL_VERSION));

* In FB SDK 3.5.2 this is already fixed

Available Facebook permissions:

    https://developers.facebook.com/docs/reference/fql/permissions/
