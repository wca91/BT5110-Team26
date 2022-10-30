#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from example.models import Models
from example import utils
import configparser




def main():
    """Run administrative tasks."""
    models = Models()
    models.createModels()

    config = configparser.ConfigParser()

# Just a small function to write the file
    def write_file():
        config.write(open('insert_sql.ini', 'w'))

    if not os.path.exists('insert_sql.ini'):
        config['insert'] = {'sql_inserted' : "0"}
        write_file()
        sql_insert = "1"
        utils.readDbFile("example/fact_table.sql", models)
        utils.readDbFile("example/crane.sql", models)
        utils.readDbFile("example/verifier.sql", models)
        utils.readDbFile("example/date.sql", models)

    else:
        # Read File

        config.read('insert_sql.ini')

        # Print value
        sql_insert = (config.get('insert', 'sql_inserted'))


    if sql_insert == "1":
        print('updating file')
        config.set('insert', 'sql_inserted',"1")
        write_file()
    elif sql_insert == "0":
        utils.readDbFile("example/fact_table.sql", models)
        utils.readDbFile("example/crane.sql", models)
        utils.readDbFile("example/verifier.sql", models)
        utils.readDbFile("example/date.sql", models)
        print('updating file')
        config.set('insert', 'sql_inserted',"1")
        write_file()
    #utils.readDbFile("example/date.sql", models)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)



if __name__ == '__main__':
    main()

