try:
    from setuptools import setup
except ImportError:
    # can't have the entry_points option here.
    from distutils.core import setup

with open('README.md') as f:
    long_description = f.read()

setup(name='sonic-client',
      version='0.0.3',
      author="Ahmed T. Youssef",
      author_email="xmonader@gmail.com",
      description='python client for sonic search backend',
      long_description=long_description,
      long_description_content_type="text/markdown",
      packages=['sonic'],
      url="https://github.com/xmonader/python-sonic-client",
      license='BSD 3-Clause License',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
      ],
      )
