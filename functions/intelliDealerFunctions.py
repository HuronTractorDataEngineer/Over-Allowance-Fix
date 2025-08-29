import pyodbc
import codecs
import logging
import pandas as pd
import os
from typing import Dict, Optional


def read_id_config():
    """
    Retrieve IntelliDealer connection settings from environment variables only.
    Requires: ID_SERVER, ID_DATABASE, ID_USER, ID_PASSWORD
    """
    env_conf = {
        "server":   os.getenv("ID_SERVER"),
        "database": os.getenv("ID_DATABASE"),
        "user":     os.getenv("ID_USER"),
        "password": os.getenv("ID_PASSWORD"),
    }

    missing = [k for k, v in env_conf.items() if not v]
    if missing:
        logging.error("IntelliDealer env vars missing: %s", ", ".join(missing))
        raise RuntimeError("Missing IntelliDealer environment variables: " + ", ".join(missing))

    logging.info("IntelliDealer Connection settings retrieved")
    return env_conf

# ------------------------------------------------------------
# Data Retreival functions — Populate Dataframes
# ------------------------------------------------------------

def retrieve_id_data(sqlDirectory: str, sqlFileName: str, id_conf: Dict[str, str], logMinutesStart: Optional[str] = None, logMinutesEnd: Optional[str] = None, logInterval: Optional[str] = None) -> pd.DataFrame:
    """
    Retrieve data using an SQL script and IntelliDealer connection info from id_conf.
    id_conf must include: server, database, user, password.
    """
    logging.info('Executing: retrieve_id_data')

    connection = None
    try:
        logging.info(' - Connecting to Database')
        connection = pyodbc.connect(
            driver='{iSeries Access ODBC Driver}',
            system=str(id_conf['server']),
            DBQ=str(id_conf['database']),
            uid=str(id_conf['user']),
            pwd=str(id_conf['password'])
        )
        logging.info(' - Connected')

        logging.info(f' - Reading {sqlFileName} SQL Script')
        sql_file_path = f'{sqlDirectory}/{sqlFileName}.sql'
        with codecs.open(sql_file_path, 'r', encoding='utf-8-sig') as file:
            sql_query_template = file.read()

        getReceivingdata = sql_query_template.format(logMinutesStart=logMinutesStart,logMinutesEnd=logMinutesEnd,logInterval=logInterval)
        logging.info(' - Executing SQL Script and Loading into DataFrame')
        df = pd.read_sql(sql=getReceivingdata, con=connection)
        df = df.convert_dtypes()
        logging.info(' - Data Loaded into DataFrame')
        return df

    except pyodbc.ProgrammingError as e:
        logging.error(f' - Programming Error occurred: {e}')
    except pyodbc.Error as e:
        logging.error(f' - Database error occurred: {e}')
    except Exception as e:
        logging.error(f' - An unexpected error occurred: {e}')
    finally:
        if connection:
            connection.close()
        logging.info(' - Cursor and Connection Closed')

def id_sqlScript(sqlDirectory: str, sqlFileName: str, id_conf: Dict[str, str]):
    """
    Execute a statement from an SQL file on a specified iSeries Access IBM DB2 database.

    This function establishes a connection to a specified database using provided credentials,
    reads an SQL script from a given file, executes the script, and commits the changes.
    It handles exceptions related to database connections and SQL execution, and ensures that the
    database connection is properly closed after execution.

    Notes:
    - The function logs various stages of execution and errors using the logging module.
    - Ensure that the 'iSeries Access ODBC Driver' is installed and correctly configured on the system.
    - The SQL script file should be encoded in 'utf-8-sig'.
    """
    logging.info(f'Executing: execute_update_statement function')

    # Initializing Connection
    connection = None

    try:
        # Connect to the database
        logging.info(' - Connecting to Database')
        connection = pyodbc.connect(
            driver='{iSeries Access ODBC Driver}',
            system=str(id_conf['server']),
            DBQ=str(id_conf['database']),
            uid=str(id_conf['user']),
            pwd=str(id_conf['password']),
            cmt=0)  # Important for transaction management
        logging.info(' - Connected')

        # Access and read SQL script with 'utf-8-sig' encoding
        logging.info(f' - Reading {sqlFileName} SQL Script')
        sql_file_path = f'{sqlDirectory}/{sqlFileName}.sql'
        with codecs.open(sql_file_path, 'r', encoding='utf-8-sig') as file:
            sql_update_statement = file.read()

        # Execute SQL update statement
        logging.info(f' - Executing {sqlFileName} SQL Statement')
        cursor = connection.cursor()
        cursor.execute(sql_update_statement)
        connection.commit()  # Commit the transaction
        logging.info(f' - {sqlFileName} Executed and Committed')

    except pyodbc.ProgrammingError as e:
        logging.error(f' - Programming Error occurred: {e}')
        if connection:
            connection.rollback()  # Rollback in case of error
    except pyodbc.Error as e:
        logging.error(f' - Database error occurred: {e}')
        if connection:
            connection.rollback()
    except Exception as e:
        logging.error(f' - An unexpected error occurred: {e}')
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()
            logging.info(' - Connection Closed')