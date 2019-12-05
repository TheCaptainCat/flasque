import setuptools
from distutils.core import setup

setup(
    name='Bolinette',
    packages=[
        'bolinette',
        'bolinette.cli',
        'bolinette.cli.commands',
        'bolinette.cli.nodes',
        'bolinette.controllers',
        'bolinette.marshalling',
        'bolinette.models',
        'bolinette.services',
        'bolinette.testing'
    ],
    version='0.0.12',
    license='MIT',
    description='Bolinette, a web framework built on top of Flask',
    author='Pierre Chat',
    author_email='pierrechat89@hotmail.fr',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Flask', 'Bolinette', 'Web', 'Framework'],
    install_requires=[
        'Flask==1.1.1',
        'Flask-Bcrypt==0.7.1',
        'Flask-Cors==3.0.8',
        'Flask-JWT-Extended==3.24.1',
        'Flask-Script==2.0.6',
        'Flask-SQLAlchemy==2.4.1',
        'Jinja2==2.10.3',
        'PyJWT==1.7.1',
        'pytest==5.3.1',
        'PyYAML==5.2',
        'SQLAlchemy==1.3.11',
        'twine==3.1.1',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
    setup_requires=[
        'wheel'
    ],
    entry_points= {
        'console_scripts': [
            'blnt=bolinette.cli:main'
        ]
    },
)
