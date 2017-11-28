from setuptools import setup, find_packages
setup(
    name="jautolock",
    version="1.0",
    packages=find_packages(),
    install_requires=["pyxdg >= 0.25", "python-xlib >= 0.20"],
    zip_safe=True,

    entry_points= {
        'console_scripts': [
            'jautolock = jautolock.main:main'
        ]
    },

    author = "John Chen",
    author_email = "johnchen902@gmail.com",
    description = "Fire up program in case of user inactivity",
    license = "GPL3",
    url = "https://github.com/johnchen902/python-jautolock",
)
