from setuptools import setup, find_packages

setup(
    name="web-server",
    version="1.0.0",
    description="Web Server with GTD Task Management",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests",
        "beautifulsoup4",
        "psutil",
    ],
    entry_points={
        "console_scripts": [
            "web-server=web_server.server:main",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
