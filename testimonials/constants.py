from django.utils.translation import gettext_lazy as _
from django.db import models


class TestimonialStatus(models.TextChoices):
    """
    Enum for testimonial statuses.
    """
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    FEATURED = "featured", _("Featured")
    ARCHIVED = "archived", _("Archived")

    @classmethod
    def get_published_statuses(cls):
        return [cls.APPROVED, cls.FEATURED]


class TestimonialSource(models.TextChoices):
    """
    Enum for testimonial sources.
    """
    WEBSITE = "website", _("Website")
    MOBILE_APP = "mobile_app", _("Mobile App")
    EMAIL = "email", _("Email")
    THIRD_PARTY = "third_party", _("Third Party")
    SOCIAL_MEDIA = "social_media", _("Social Media")
    OTHER = "other", _("Other")


class TestimonialMediaType(models.TextChoices):
    """
    Enum for testimonial media types.
    """
    IMAGE = "image", _("Image")
    VIDEO = "video", _("Video")
    AUDIO = "audio", _("Audio")
    DOCUMENT = "document", _("Document")


class AuthorTitle(models.TextChoices):
    """Professional title choices for testimonial authors."""
    
    # Executive Titles
    CEO = 'CEO', _('CEO')
    CTO = 'CTO', _('CTO')
    CFO = 'CFO', _('CFO')
    COO = 'COO', _('COO')
    PRESIDENT = 'President', _('President')
    VICE_PRESIDENT = 'Vice President', _('Vice President')
    EXECUTIVE_DIRECTOR = 'Executive Director', _('Executive Director')
    FOUNDER = 'Founder', _('Founder')
    CO_FOUNDER = 'Co-Founder', _('Co-Founder')
    
    # Management Titles
    DIRECTOR = 'Director', _('Director')
    SENIOR_DIRECTOR = 'Senior Director', _('Senior Director')
    MANAGER = 'Manager', _('Manager')
    SENIOR_MANAGER = 'Senior Manager', _('Senior Manager')
    PROJECT_MANAGER = 'Project Manager', _('Project Manager')
    PRODUCT_MANAGER = 'Product Manager', _('Product Manager')
    TEAM_LEAD = 'Team Lead', _('Team Lead')
    DEPARTMENT_HEAD = 'Department Head', _('Department Head')
    
    # Professional Titles
    SENIOR_CONSULTANT = 'Senior Consultant', _('Senior Consultant')
    CONSULTANT = 'Consultant', _('Consultant')
    SPECIALIST = 'Specialist', _('Specialist')
    ANALYST = 'Analyst', _('Analyst')
    COORDINATOR = 'Coordinator', _('Coordinator')
    SUPERVISOR = 'Supervisor', _('Supervisor')
    
    # Technical Titles
    SENIOR_DEVELOPER = 'Senior Developer', _('Senior Developer')
    SOFTWARE_ENGINEER = 'Software Engineer', _('Software Engineer')
    LEAD_DEVELOPER = 'Lead Developer', _('Lead Developer')
    ARCHITECT = 'Architect', _('Architect')
    TECHNICAL_LEAD = 'Technical Lead', _('Technical Lead')
    
    # Marketing & Sales
    MARKETING_MANAGER = 'Marketing Manager', _('Marketing Manager')
    SALES_MANAGER = 'Sales Manager', _('Sales Manager')
    ACCOUNT_MANAGER = 'Account Manager', _('Account Manager')
    BUSINESS_DEVELOPMENT = 'Business Development Manager', _('Business Development Manager')
    
    # Academic & Professional Services
    PROFESSOR = 'Professor', _('Professor')
    DR = 'Dr.', _('Dr.')
    ATTORNEY = 'Attorney', _('Attorney')
    PRINCIPAL = 'Principal', _('Principal')
    
    # Customer/Client Titles
    CUSTOMER = 'Customer', _('Customer')
    CLIENT = 'Client', _('Client')
    USER = 'User', _('User')
    MEMBER = 'Member', _('Member')
    OTHER = "Other", _('Other')

