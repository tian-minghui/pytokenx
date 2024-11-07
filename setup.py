from setuptools import setup, find_packages

setup(
    name="pytoken",
    version="0.1",
    packages=find_packages(),
    author="timway",
    author_email="tianmh2013@163.com",
    description="A token manager for Python",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tian-minghui/pytoken",
)