class TestimonialError(Exception):
    """Base exception for all testimonial-related errors."""
    pass


class TestimonialValidationError(TestimonialError):
    """Exception raised when testimonial validation fails."""
    pass


class TestimonialPermissionError(TestimonialError):
    """Exception raised when a user doesn't have permission to perform an action."""
    pass


class TestimonialConfigurationError(TestimonialError):
    """Exception raised when there's a configuration error."""
    pass


class TestimonialMediaError(TestimonialError):
    """Exception raised when there's an error with testimonial media."""
    pass