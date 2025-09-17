from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-testimonials",
    version="0.1.0",
    author="Ifeanyi Stanley Nnamani",
    author_email="nnamaniifeanyi10@gmail.com",
    description="A comprehensive, reusable Django testimonials package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NzeStan/django-testimonials",
    project_urls={
        "Bug Tracker": "https://github.com/NzeStan/django-testimonials/issues",
        "Documentation": "https://django-testimonials.readthedocs.io/",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 4.1",
        "Framework :: Django :: 4.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "Django>=3.2",
        "djangorestframework>=3.12.0",
        "Pillow>=8.0.0",
        "django-filter>=2.4.0",
        "django-phonenumber-field[phonenumbers]>=7.0.0",
    ],
    extras_require={
        "dev": [
        "pytest>=7.0.0",
        "pytest-django>=4.5.0",
        "factory-boy>=3.2.0",
        "coverage>=6.0.0",
        "ruff>=0.1.0",
        "mkdocs>=1.3.0",
        "mkdocs-material>=8.0.0",
        ],
    },
    zip_safe=False,
)