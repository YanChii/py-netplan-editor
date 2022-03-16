import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "netplan_editor",
    version = "0.0.2",
    author = "YanChii",
    author_email = "janci@binaryparadise.com",
    description = "Library for searching and editing netplan yaml config files",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/yanchii/py-netplan-editor",
    project_urls = {
        "Bug Tracker": "https://github.com/yanchii/py-netplan-editor/issues",
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache License",
        "Operating System :: OS Independent",
    ],

    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),

    python_requires=">=3.6",
    install_requires = [
        "dpath",
	"pyyaml",
    ],
    entry_points = {
        'console_scripts': [
            'update-netplan = netplan_editor.update_netplan_cmd:update_netplan',
        ],
    },
)
