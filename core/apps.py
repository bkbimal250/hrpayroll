from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Disable last_login signal to prevent UUID field update issues
        from django.contrib.auth.signals import user_logged_in
        from django.contrib.auth.models import update_last_login
        
        # Disconnect the update_last_login function
        try:
            user_logged_in.disconnect(update_last_login)
        except:
            # Signal might already be disconnected
            pass
        
        # Override the update_last_login function to do nothing
        def dummy_update_last_login(sender, user, **kwargs):
            pass
        
        # Also monkey patch the update_last_login function directly
        import django.contrib.auth.models
        django.contrib.auth.models.update_last_login = dummy_update_last_login
        
        # Also patch the function in the auth module
        import django.contrib.auth
        django.contrib.auth.update_last_login = dummy_update_last_login
        
        # Import signals to ensure they are connected
        import core.signals