from setuptools import setup, find_packages

setup(name="mess_server_jim",
      version="0.0.1",
      description="Mess Server",
      author="AlisaEAS",
      author_email="alisa.eas@yandex.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex'],
      scripts=['server/server_run']
      )
