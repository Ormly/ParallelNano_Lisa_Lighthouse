import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="TPRO",
    version="0.0.1",
    author="Chen Kasirer",
    author_email="chen902@gmail.com",
    description="Lighthouse Monitoring API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ormly/ParallelNano_Lisa_Lighthouse",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "gunicorn",
        "ipcqueue",
        "flask",
        "readerwriterlock"
    ]
)
