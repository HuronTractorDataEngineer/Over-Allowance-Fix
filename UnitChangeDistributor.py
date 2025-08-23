import logging
import datetime
from functions.intelliDealerFunctions import retrieve_id_data, read_id_config, calc_log_variables
from functions.warehouseFunctions import retrieve_server_data, read_dw_config
from functions.graphFunctions import send_email_graph, read_graph_config
from functions.evaluationFunctions import compile_change_list_for_user, append_Salesmen_to_dfAlertUsers, compile_change_list_for_Salesmen
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

# Extend Alert Users to contain Salespeople
# Disabled for now during pilot phase

#dfAlertUsers = append_Salesmen_to_dfAlertUsers(dfAlertUsers, dfChangeLog)

# ------------------------------------------------------------
# Main Orchestrator
# ------------------------------------------------------------
def main():
    """
    Compile per-user change lists, and email results via Graph.
    """

    # Initialize Counts
    logging.info('Initilizing Counts')
    processed = 0
    sent = 0

    # Loop through compiling table and sending email for each user.
    logging.info('Starting Alert User Processing Loop')
    for _, user in dfAlertUsers.iterrows():

        # Assign Current User attributes
        email = str(user.get('Email') or '').strip()
        name = str(user.get('Name') or '').strip()
        role  = str(user.get('Role')  or '').strip()
        branch= str(user.get('Branch')or '').strip()

        # Checking for missing values
        if not email or not name or not role or not branch:
            logging.warning(f'Skipping user with missing fields: email={email}, name={name}, role={role}, branch={branch}')
            continue
        
        # Compile Chance List choosing correct method based on if Role is Salesperson
        if role == "Salesperson":
            df_user = compile_change_list_for_Salesmen(WANTED_COLUMNS, dfChangeLog, email)
        else:
            df_user = compile_change_list_for_user(WANTED_COLUMNS, dfChangeLog, dfAlertMatrix, branch, role)

        processed += 1

        # Confirming List contains data, if not record in log and skip to next user
        if df_user.empty:
            logging.info(f'No matching changes for {email} ({role} @ {branch}).')
            continue

        # Sort by STATUS priority (then EVENT_TS desc) and render colored table
        df_send = sort_for_email(_STATUS_RANK, df_user.copy())

        # Setting Email variables
        subject = f"Unit Changes for {name} — {role} ({len(df_send)} records)"
        title   = f"Unit Changes for {name} — {role}"
        subtitle= f"Total records: {len(df_send)} (sorted by STATUS)"

        # Rendering HTML email
        body_html = render_html_table(_STATUS_RANK, STATUS_COLORS, REPORT_URL, REPORT_LABEL, df_send, title=title, subtitle=subtitle)
        
        # Sending email to user
        try:
            send_email_graph(email, subject, body_html, graph_conf)
            sent += 1
        except Exception as e:
            logging.exception(f'Failed for {email}: {e}')
            continue

    # Removing old Log files
    logging.info(f'Removing old logs.')
    remove_old_files('logs', 10)

    logging.info(f'User Processing complete. Users processed: {processed}; Emails sent: {sent}.')  

if __name__ == '__main__':
    main()
