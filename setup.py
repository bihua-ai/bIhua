# python setup.py sdist bdist_wheel
# pip install dist/your_package_name-version-py3-none-any.whl
# pip install dist/your_package_name-version.tar.gz
# pip install -e .
# pip uninstall bihua  # Replace with your package name
# pip install bihua  # Replace with your package name


from setuptools import setup, find_packages

setup(
    name='bihua',  # Name of your package
    version='0.0.1',  # Initial version
    packages=find_packages(include=['bihua', 'bihua.*']),  # Automatically find all packages
    install_requires=[  # Any dependencies
        # Example:
        # 'numpy',
    ],
    python_requires='>=3.10',  # Specify Python version requirement
    author='Eric Lee',
    author_email='eric.lee@bihua.ai',
    description='A package for bihua.ai',  # A short description
    long_description=open('README.md').read(),  # If you have a README.md
    long_description_content_type='text/markdown',  # Markdown format for README
    url='https://github.com/bihua-ai/bihua',  # Your GitHub repo URL
    classifiers=[  # Classifiers help others find your project
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3 :: Only',
    ],
    license='ERIC LEE', 
    extras_require={  # Optional dependencies
        'dev': ['pytest', 'sphinx'],
    },
    tests_require=[  # Testing dependencies
        'pytest',
    ],
)

