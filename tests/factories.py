# testimonials/factories.py
import factory
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from testimonials.models import Testimonial, TestimonialCategory, TestimonialMedia
from testimonials.constants import TestimonialStatus, TestimonialSource, TestimonialMediaType

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    __test__ = False
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class AdminUserFactory(UserFactory):
    """Admin user with superuser/staff permissions."""
    is_staff = True
    is_superuser = True
    username = "adminuser"
    email = "admin@example.com"
    password = factory.PostGenerationMethodCall("set_password", "adminpass123")


class TestimonialCategoryFactory(factory.django.DjangoModelFactory):
    __test__ = False
    class Meta:
        model = TestimonialCategory
        skip_postgeneration_save = True

    name = factory.Faker("word")
    description = factory.Faker("sentence")
    is_active = True


class TestimonialFactory(factory.django.DjangoModelFactory):
    __test__ = False
    class Meta:
        model = Testimonial
        skip_postgeneration_save = True

    author = factory.SubFactory(UserFactory)
    author_name = factory.Faker("name")
    author_email = factory.Faker("email")
    author_title = factory.Faker("job")
    company = factory.Faker("company")
    location = factory.Faker("city")
    title = factory.Faker("sentence", nb_words=4)
    content = factory.Faker("paragraph", nb_sentences=3)
    rating = 5 
    category = factory.SubFactory(TestimonialCategoryFactory)
    status = TestimonialStatus.APPROVED
    source = TestimonialSource.WEBSITE
    is_anonymous = False


class PendingTestimonialFactory(TestimonialFactory):
    status = TestimonialStatus.PENDING
    author_name = "Pending User"
    author_email = "pending@example.com"


class FeaturedTestimonialFactory(TestimonialFactory):
    status = TestimonialStatus.FEATURED
    author_name = "Featured User"
    author_email = "featured@example.com"
    company = "Featured Company"


class AnonymousTestimonialFactory(TestimonialFactory):
    author = None
    author_name = "Anonymous"
    is_anonymous = True
    status = TestimonialStatus.APPROVED


class TestimonialMediaFactory(factory.django.DjangoModelFactory):
    __test__ = False
    class Meta:
        model = TestimonialMedia
        skip_postgeneration_save = True

    testimonial = factory.SubFactory(TestimonialFactory)
    title = "Test Image"
    description = "A test image"
    media_type = TestimonialMediaType.IMAGE

    # Instead of writing an actual file, we generate in-memory bytes
    file = factory.LazyAttribute(
        lambda _: ContentFile(
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x0a\x00\x01\x00,\x00"
            b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;",
            name="test_image.gif",
        )
    )
