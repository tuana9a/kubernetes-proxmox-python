import setuptools

setuptools.setup(name="kp",
                 packages=setuptools.find_packages(exclude=["test"]),
                 python_requires=">=3.8",
                 version="1.0.0",
                 author="Nguyen Minh Tuan",
                 author_email="tuana9a@gmail.com",
                 entry_points={"console_scripts": [
                     "kp=cli.main:main",
                 ]},
                 install_requires=["requests==2.31.0", "proxmoxer==2.0.1"])
