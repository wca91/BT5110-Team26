from collections import namedtuple


def namedtuplefetchall(cursor):
    "Return all rows from a cursor as a namedtuple"
    nt_result = namedtuple('Result', [col[0] for col in cursor.description])
    return [nt_result(*row) for row in cursor.fetchall()]


def clamp(value, minimum, maximum):
    """Clamp a value between a minimum and maximum value"""
    return max(minimum, min(value, maximum))

def readDbFile(filename, models):
    # Open the .sql file
    sqlFile = open(filename,'r')

    # Create an empty command string
    sqlCommand = ''

    # Iterate over all lines in the sql file
    for line in sqlFile:
        # Ignore commented lines
        if not line.startswith('--') and line.strip('\n'):
            # Append line to the command string
            sqlCommand += line.strip('\n')

            # If the command string ends with ';', it is a full statement
            if sqlCommand.endswith(';'):
                # Try to execute statement and commit it
                try:
                    print(sqlCommand)
                    models.executeRawSql(sqlCommand)

                # Assert in case of error
                except:
                    print('No insertion made. Check if there are primary key conflicts: ' + sqlCommand)

                # Finally, clear command string
                finally:
                    sqlCommand = ''
