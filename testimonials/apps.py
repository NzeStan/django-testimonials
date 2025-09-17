from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TestimonialsConfig(AppConfig):
    name = 'testimonials'
    verbose_name = _("Testimonials")
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures that the signal handlers are connected.
        """
        import testimonials.signals  # noqa