import os
import pyodbc
import logging
import pandas as pd
from typing import Dict

def read_dw_config():
    """
    Retrieve Data Warehouse connection settings from environment variables only.
    Requires: DW_SERVER, DW_DATABASE, DW_USER, DW_PASSWORD
    """
    conf = {
        "server":   os.getenv("DW_SERVER"),
        "database": os.getenv("DW_DATABASE"),
        "user":     os.getenv("DW_USER"),
        "password": os.getenv("DW_PASSWORD"),
    }

    missing = [k for k, v in conf.items() if not v]
    if missing:
        logging.error("Data Warehouse env vars missing: %s", ", ".join(missing))
        raise RuntimeError("Missing Data Warehouse environment variables: " + ", ".join(missing))

    logging.info("Data Warehouse connection settings retrieved")
    return conf

def retrieve_server_data(tblName: str, dw_conf: Dict[str, str]) -> pd.DataFrame:
    """
    Retrieve data using from table in SQL server from id_conf.
    id_conf must include: server, database, user, password.
    """
    connection = None
    df = pd.DataFrame()

    try:
        logging.info(f"Connecting to {dw_conf['database']} on {dw_conf['server']}")
        
        # Connect to SQL Server
        connection = pyodbc.connect(
            driver='{SQL Server}',
            server=str(dw_conf['server']),
            database=str(dw_conf['database']),
            UID=str(dw_conf['user']),
            PWD=str(dw_conf['password']),
            autocommit=False
        )

        query = f"SELECT * FROM {tblName}"
        df = pd.read_sql(query, connection)

        logging.info(f"Fetched {len(df)} rows from {tblName}.")

    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
    finally:
        if connection:
            connection.close()
        logging.info(' - Connection Closed')

    return df