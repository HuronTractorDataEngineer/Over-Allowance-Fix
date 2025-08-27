import logging
import datetime
from functions.intelliDealerFunctions import id_sqlScript, retrieve_id_data, read_id_config, calc_log_variables
from functions.warehouseFunctions import retrieve_server_data, read_dw_config
from functions.graphFunctions import send_email_graph, read_graph_config
from functions.evaluationFunctions import build_dfUsers_from_df, compile_change_list_for_user, compile_change_list_for_Salesmen, append_Salesmen_to_dfAlertUsers
from functions.renderingFunctions import load_htmlTable_settings, sort_for_email, render_html_table
from functions.maintenanceFunctions import remove_old_files

# ------------------------------------------------------------
# Job and Logging Configuration
# ------------------------------------------------------------

# Set Runtime variables
logMinutesStart, logMinutesEnd, logInterval = calc_log_variables()
jobName = 'OverAllowAccFix'

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

sqlDirectory = 'sql\OverAllowAccFix'
#id_sqlScript(sqlDirectory, 'removeOldIssues', id_conf)
#id_sqlScript(sqlDirectory, 'insertNewIssues', id_conf)
#id_sqlScript(sqlDirectory, 'fixIssues', id_conf)

df = retrieve_id_data(sqlDirectory, 'pullData', id_conf)
print(df)

dfUsers = build_dfUsers_from_df(df)
print(dfUsers)