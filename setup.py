"""
Create/Fix setup.py to support pip install django-testimonials[performance]
"""

# setup.py
from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()

# Base requirements
INSTALL_REQUIRES = [
    'Django>=4.2,<5.0',
    'djangorestframework>=3.12.0',
    'django-filter>=22.1',
    'django-phonenumber-field[phonenumbers]>=7.0.0',
    'Pillow>=8.0.0',
]

# Performance extras
PERFORMANCE_REQUIRES = [
    'django-redis>=5.2.0',
    'celery[redis]>=5.2.0',
    'redis>=4.3.0',
]

# Development extras
DEV_REQUIRES = [
    'pytest>=7.0.0',
    'pytest-django>=4.5.0',
    'pytest-cov>=4.0.0',
    'black>=22.0.0',
    'flake8>=5.0.0',
    'pre-commit>=2.20.0',
    'factory-boy>=3.2.0',
    'Faker>=15.0.0',
]

setup(
    name='django-testimonials',
    version='1.0.0',
    description='High-performance Django package for managing customer testimonials at scale',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='NzeStan',
    author_email='nnamaniifeanyi10@gmail.com',
    url='https://github.com/NzeStan/django-testimonials',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    extras_require={
        'performance': PERFORMANCE_REQUIRES,
        'dev': DEV_REQUIRES + PERFORMANCE_REQUIRES,
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Framework :: Django :: 4.1',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    python_requires='>=3.8',
    keywords='django testimonials reviews feedback api rest',
)
