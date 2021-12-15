from setuptools import setup, find_packages


with open("./requirements.txt") as fp:
    dependencies = [line.strip() for line in fp.readlines()]

setup(
    name="Chen Immigration",
    version="0.1.0",
    description="Scrapes I140 Forms from Chen Immigration Website and Analyzes Wait Times",
    author="Christian Adib",
    author_email="christian.adib@gmail.com",
    packages=find_packages(),
    install_requires=dependencies,
)
