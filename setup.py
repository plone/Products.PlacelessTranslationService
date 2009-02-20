from setuptools import setup, find_packages
import sys, os

version = '1.5'

setup(name='Products.PlacelessTranslationService',
      version=version,
      description="PTS provides a way of internationalizing (i18n'ing) and "
                  "localizing (l10n'ing) software for Zope 2.",
      long_description=open("readme.txt").read() + "\n" +
                       open("CHANGES.txt").read(),
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
      ],
      keywords='Zope CMF Plone i18n l10n translation gettext',
      author='Lalo Martins',
      author_email='plone-developers@lists.sourceforge.net',
      url='http://pypi.python.org/pypi/Products.PlacelessTranslationService',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
      ],
)
