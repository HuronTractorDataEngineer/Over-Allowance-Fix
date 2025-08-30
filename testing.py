import logging
import datetime
from functions.intelliDealerFunctions import id_sqlScript, retrieve_id_data, read_id_config
from functions.graphFunctions import send_email_graph, read_graph_config
from functions.evaluationFunctions import build_dfUsers_from_df, compile_error_list
from functions.renderingFunctions import load_htmlTable_settings, sort_for_email, render_html_table
from functions.maintenanceFunctions import remove_old_files

# ------------------------------------------------------------
# Job and Logging Configuration
# ------------------------------------------------------------
jobName = 'OverAllowAccFix'
sqlDirectory = 'sql'

# Initialize Log file
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
WANTED_COLUMNS, STATUS_COLORS, STATUS_ORDER, CC = load_htmlTable_settings()

# Precompute rank mapping for fast sort (higher rank = earlier in table)
# reversed() + start=1 → items at the start of STATUS_ORDER get the highest rank
_STATUS_RANK = {s.lower(): rank for rank, s in enumerate(reversed(STATUS_ORDER), start=1)}

logging.info(' - Table Preferences loaded')


# ------------------------------------------------------------
# Find, log and fix Overallowance Account issues
# ------------------------------------------------------------
logging.info('Processing Fixes...')

id_sqlScript(sqlDirectory, 'removeOldIssues', id_conf)
logging.info(' - Removed old issues')
