from kivy import platform

__all__=('Facebook',)

if platform() == 'android':
    from androidfacebook import AndroidFacebook as Facebook
else:
    from mockfacebook import MockFacebook as Facebook
