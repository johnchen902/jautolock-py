from setuptools import setup, find_packages
setup(
    name="jautolock",
    version="0.9",
    packages=find_packages(),
    install_requires=["pyxdg >= 0.25", "python-xlib >= 0.20"],

    entry_points= {
        'console_scripts': [
            'jautolock = jautolock.main:main'
        ]
    },

    author = "John Chen",
    author_email = "johnchen902@gmail.com",
    description = "Automatic X screen-locker/screen-saver",
    license = "AGPL",
    url = "https://github.com/johnchen902/jautolock-py",
)
