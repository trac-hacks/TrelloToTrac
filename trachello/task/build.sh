#!/bin/bash
cd ..
python setup.py bdist_egg
echo '---------------------------copio------------------------------------------------'
sudo cp dist/TracHello-0.1-py2.7.egg /var/enabu-env/python/lib/python2.7/site-packages/
sudo service apache2 restart

