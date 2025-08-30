import pyodbc
import codecs
import logging
import pandas as pd
import os
from typing import Dict, Optional

# ------------------------------------------------------------
# IntelliDealer Config Reader
# ------------------------------------------------------------
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
# Data Retreival function — Populate Dataframes
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


# ------------------------------------------------------------
# Data minipulation function - Script runner
# ------------------------------------------------------------
def _split_sql_on_semicolons(sql: str) -> list[str]:
    # strip a possible BOM and split on ';'
    return [s.strip() for s in sql.replace('\ufeff', '').split(';') if s.strip()]

def id_sqlScript(sqlDirectory: str, sqlFileName: str, id_conf: Dict[str, str]):
    """
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
            script = file.read()

        statements = _split_sql_on_semicolons(script)
        logging.info(f' - Found {len(statements)} statement(s)')

        # Execute SQL update statement
        logging.info(f' - Executing {sqlFileName} SQL Statement')
        cursor = connection.cursor()

        # Looping through Statements
        for i, stmt in enumerate(statements, 1):
            try:
                logging.info(f'   -> Executing [{i}/{len(statements)}]')
                cursor.execute(stmt)
            except Exception as e:
                logging.error(f'   !! Failed on statement {i}: {stmt[:200]}...')
                raise

        logging.info(f' - {sqlFileName} executed (CMT=0: statements are permanent)')

    except pyodbc.ProgrammingError as e:
        logging.error(f' - Programming Error occurred: {e}')
    except pyodbc.Error as e:
        logging.error(f' - Database error occurred: {e}')
    except Exception as e:
        logging.error(f' - An unexpected error occurred: {e}')
    finally:
        if connection:
            cursor.close
            connection.close()
            logging.info(' - Cursor and Connection Closed')