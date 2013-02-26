#!/bin/bash
sudo service postgresql restart

echo "cancello db"
dropdb -h pgsql --username=postgres trac-enabu

echo "ricreo il db"
psql -U postgres < createdb.sql

echo "importo il dump"
psql -U postgres -W trac-enabu < trac.dump 
