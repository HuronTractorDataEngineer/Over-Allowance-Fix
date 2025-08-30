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

def first_comment_line(stmt: str) -> str:
    s = stmt.lstrip().replace('\r\n', '\n').replace('\r', '\n')
    line = s.split('\n', 1)[0]              # first line only
    if line.startswith('--'):
        return line[2:].strip()             # drop '--'
    if line.startswith('/*'):
        return line[2:].split('*/', 1)[0].lstrip('*').strip()  # first part of a block comment
    return line.strip()                      # fallback (in case a comment isn't present)

def id_sqlScript(sqlDirectory: str, sqlFileName: str, id_conf: Dict[str, str]):
    """
    Execute an IBM i (iSeries) SQL script via ODBC, statement by statement.

    Opens `{sqlDirectory}/{sqlFileName}.sql` (UTF-8-SIG), splits on semicolons,
    and runs each statement using the iSeries Access ODBC driver. Logs the
    connection steps, a title for each statement (from its first comment, if any),
    and the rows affected. Uses `cmt=0` (autocommit), so each statement is
    committed immediately.
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

        # Create statement list
        statements = _split_sql_on_semicolons(script)
        logging.info(f' - Found {len(statements)} statement(s)')

        # Initialize cursor
        logging.info(f' - Initializing cursor')
        cursor = connection.cursor()

        # Looping through Statements
        for i, stmt in enumerate(statements, 1):
            try:
                # Pull comment as title, log statement being run, run statement, log effected row count
                title = first_comment_line(stmt) or " ".join(stmt.split())[:120]
                logging.info(f'   -> Executing [{i}/{len(statements)}]: {title}')
                cursor.execute(stmt)
                rows = cursor.rowcount
                logging.info(f'           -> {rows} effected by statement')
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
        if cursor is not None:
            cursor.close()
        if connection:
            connection.close()
        logging.info(' - Cursor and Connection Closed')
