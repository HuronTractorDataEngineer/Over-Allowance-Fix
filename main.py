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
# Main Orchestrator
# ------------------------------------------------------------
def main():
    """
    Orchestrate the Over Allowance Fix job.

    Workflow:
        1) Load IntelliDealer (DB2) and Microsoft Graph configs.
        2) Load HTML table preferences and compute a status-priority map.
        3) Execute `sql/fixScript.sql` to rebuild the working table and update
           Pending/Released items in IntelliDealer (Invoiced excluded).
        4) Retrieve the ErrorLog dataset and derive:
           - per-user error lists (for settlement users)
           - the Invoiced subset (last 30 days) for reviewer oversight.
        5) For each user with data: sort by status priority, render an HTML table,
           and email via Graph (with configured CC).
        6) If Invoiced issues exist, email a summary to the designated reviewer.
        7) Rotate logs, keeping the newest 10 files.

    Notes:
        Designed for unattended runs via Windows Task Scheduler
        (Mon–Fri at TO BE DETERMINED).
    """

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

    id_sqlScript(sqlDirectory, 'fixScript', id_conf)
    logging.info(' - Found, logged and fixed over allowance account issue for pending and released invoices')


    # ------------------------------------------------------------
    # Load and compile working datasets
    # ------------------------------------------------------------
    logging.info('Retrieving dataframes...')

    dfErrorLog = retrieve_id_data(sqlDirectory, 'errorLog', id_conf)
    logging.info(' - ErrorLog dataset loaded')

    dfAlertUsers = build_dfUsers_from_df(dfErrorLog)
    logging.info(' - Alert Users Loaded')

    dfInvoiced = dfErrorLog.loc[dfErrorLog['STATUS'].eq('Invoiced'), WANTED_COLUMNS].copy()
    logging.info(' - Invoiced Loaded')


    # ------------------------------------------------------------
    # Process user email notifications
    # ------------------------------------------------------------
    # Initialize Counts
    logging.info('Initializing Counts')
    processed = 0
    sent = 0

    # Loop through compiling table and sending email for each user.
    logging.info('Starting Settlement Auditor Processing Loop')
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
        
        # Compile Error List for user
        df_user = compile_error_list(WANTED_COLUMNS, dfErrorLog, email)
        processed += 1

        # Confirming List contains data, if not record in log and skip to next user
        if df_user.empty:
            logging.info(f'No matching changes for {email} ({role} @ {branch}).')
            continue

        # Sort by STATUS priority then Invoice and render colored table
        df_send = sort_for_email(_STATUS_RANK, df_user.copy())

        # Creating list of corrected records
        corrected_count = int(df_send["STATUS"].isin(["Pending", "Released"]).sum())

        # Setting Email variables
        subject  = f"Overallowance Account Errors for {name} ({len(df_send)} records; {corrected_count} auto-fixed)"
        title   = f"Pending and Released fixed / Invoiced requires journal"
        subtitle = f"Auto-fixed (Pending+Released): {corrected_count} • Total: {len(df_send)}"

        # Rendering HTML email
        body_html = render_html_table(_STATUS_RANK, STATUS_COLORS, df_send, title=title, subtitle=subtitle)
        
        # Sending email to user
        try:
            send_email_graph(email, subject, body_html, graph_conf, CC)
            sent += 1
        except Exception as e:
            logging.exception(f'Failed for {email}: {e}')
            continue
    
    # Check for Invoiced Issues, if found send to Leanne for Intervention
    if not dfInvoiced.empty:
        inv_subject  = f"Overallowance: {len(dfInvoiced)} invoiced issues requiring journal"
        inv_title    = "Invoiced requires journal"
        inv_subtitle = f"Total Invoiced records: {len(dfInvoiced)}"
        body_htmlInvoiced = render_html_table(_STATUS_RANK, STATUS_COLORS, dfInvoiced,title=inv_title, subtitle=inv_subtitle)
        send_email_graph("lsmith@hurontractor.com", inv_subject, body_htmlInvoiced, graph_conf)
        logging.info(f' - Sent Invoiced Issues to Leanne for intervention')

    # ------------------------------------------------------------
    # Log clean up
    # ------------------------------------------------------------
    # Removing old Log files
    logging.info(f'Removing old logs.')
    remove_old_files('logs', 10)

    logging.info(f'Error Processing complete. Users processed: {processed}; Emails sent: {sent}.')  


if __name__ == '__main__':
    main()