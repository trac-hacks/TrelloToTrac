from setuptools import find_packages, setup

# name can be any name.  This name will be used to create the .egg file.
# name that is used in packages is the one that is used in the trac.ini file.
# use package name as entry_points
setup(
    description='Trello plugin for Trac 0.11',
    author='Matteo Magni',
    author_email='matteo@magni.me',
    url = 'https://github.com/ilbonzo/TrelloToTrac',
    name='TracTrello', version='0.1',
    packages=find_packages(exclude=['*.tests*']),
    entry_points = """
        [trac.plugins]
        trello = trello
    """,
    package_data={'trello': ['templates/*.html',
                            'htdocs/css/*.css', 
                            'htdocs/images/*']},
)
