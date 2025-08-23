import logging
import datetime
import pandas as pd
from functions.intelliDealerFunctions import retrieve_id_data, read_id_config, calc_log_variables
from functions.warehouseFunctions import retrieve_server_data, read_dw_config
from functions.graphFunctions import send_email_graph, read_graph_config
from functions.evaluationFunctions import compile_change_list_for_user, generate_dfSalesmen, compile_change_list_for_Salesmen
from functions.renderingFunctions import load_htmlTable_settings, sort_for_email, render_html_table
from functions.maintenanceFunctions import remove_old_files

# ------------------------------------------------------------
# Job and Logging Configuration
# ------------------------------------------------------------

# Assess runtime Interval
logMinutesStart, logMinutesEnd, logInterval = calc_log_variables()

jobName = 'UnitChangeProcess'

log_filename = datetime.datetime.now().strftime(f'logs/{jobName}_%Y-%m-%d_%H-%M-%S.log')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    filename=log_filename,
                    filemode='w')

logging.info(f'{jobName} Job and Logging Config loaded')


# ------------------------------------------------------------
# Load Connection Settings
# ------------------------------------------------------------
logging.info('Loading Connection Settings...')

# Data Warehouse connection
dw_conf = read_dw_config()
logging.info(' - Data Warehouse Config loaded')

# IntelliDealer connection
id_conf = read_id_config()
logging.info(' - IntelliDealer Config loaded')

# Graph settings (required for this version)
graph_conf = read_graph_config()
logging.info(' - Microsoft Graph Config loaded')


# ------------------------------------------------------------
# Load HTML Table Preferences
# ------------------------------------------------------------
logging.info('Loading HTML Table Preferences...')

# Load HTML Table Settings
WANTED_COLUMNS, STATUS_COLORS, STATUS_ORDER, REPORT_URL, REPORT_LABEL = load_htmlTable_settings()

# Precompute rank mapping for fast sort (higher rank = earlier in table)
# reversed() + start=1 → items at the start of STATUS_ORDER get the highest rank
_STATUS_RANK = {s.lower(): rank for rank, s in enumerate(reversed(STATUS_ORDER), start=1)}
logging.info(' - Table Preferences loaded')


# ------------------------------------------------------------
# Load and compile Datasets working datasets
# ------------------------------------------------------------
logging.info('Retrieving dataframes...')

# Load IntelliDealer Change log into dataframe
dfChangeLog   = retrieve_id_data('config', 'ChangeLog', id_conf,logMinutesStart,logMinutesEnd,logInterval)
logging.info(' - Changlog dataset loaded')

# Load Alert Matrix into dataframe
dfAlertMatrix = retrieve_server_data('AlertMatrix', dw_conf)
logging.info(' - Alert Matrix loaded')

# Load Alert Users into dataframe
dfAlertUsers  = retrieve_server_data('AlertUsers', dw_conf)
logging.info(' - Alert Users Loaded')

# Create Salesmen Dataframe from dfChangeLog
dfSalesmen = generate_dfSalesmen(dfChangeLog)
dfSalesmen = dfSalesmen.assign(Role='Salesperson', Branch='All')
dfAlertUsers = pd.concat([dfAlertUsers, dfSalesmen], ignore_index=True)
print(dfAlertUsers)
print(dfSalesmen)



print(dfAlertUsers)