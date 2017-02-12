from setuptools import setup, find_packages

version = '2.0.7'

setup(
    name='Products.PlacelessTranslationService',
    version=version,
    description="PTS provides a way of internationalizing (i18n'ing) and "
                "localizing (l10n'ing) software for Zope 2.",
    long_description=(open("README.rst").read() + "\n" +
                      open("CHANGES.rst").read()),
    classifiers=[
        "Framework :: Plone",
        "Framework :: Plone :: 4.3",
        "Framework :: Plone :: 5.0",
        "Framework :: Plone :: 5.1",
        "Framework :: Zope2",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    keywords='Zope CMF Plone i18n l10n translation gettext',
    author='Lalo Martins',
    author_email='plone-developers@lists.sourceforge.net',
    url='https://pypi.python.org/pypi/Products.PlacelessTranslationService',
    license='GPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['Products'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
      'setuptools',
      'python-gettext >= 0.6',
      'zope.annotation',
      'zope.component',
      'zope.deferredimport',
      'zope.deprecation',
      'zope.i18n',
      'zope.interface',
      'zope.publisher',
      'Acquisition',
      'DateTime',
      'ExtensionClass',
      'ZODB3',
      'Zope2',
    ],
)
