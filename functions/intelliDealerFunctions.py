import pyodbc
import codecs
import logging
import pandas as pd
import os
from typing import Dict
from datetime import datetime
from zoneinfo import ZoneInfo


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

def calc_log_variables(now: datetime | None = None, tz: str = "America/Toronto") -> tuple[str, str, str]:
    """
    Calculates Minutes and Interval to be used in SQL statement
    """
    # Resolve "now" in the desired timezone
    if now is None:
        now = datetime.now(ZoneInfo(tz))
    else:
        z = ZoneInfo(tz)
        now = now if now.tzinfo else now.replace(tzinfo=z)
        now = now.astimezone(z)

    hh = now.hour
    mm = now.minute
    wd = now.weekday()  # Monday=0 ... Sunday=6

    if hh == 9 and wd == 0:
        return '30','00','65'
    if hh == 9 and wd != 0:
        return '30','00','17'
    if hh == 16 and mm == 30:
        return "00",'30','1'

    return '00','00','2'

# ------------------------------------------------------------
# Data Retreival functions — Populate Dataframes
# ------------------------------------------------------------

def retrieve_id_data(sqlDirectory: str, sqlFileName: str, id_conf: Dict[str, str], logMinutesStart: str, logMinutesEnd: str, logInterval: str) -> pd.DataFrame:
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