import os
import logging

# ------------------------------------------------------------
# Project Directory Maintenance
# ------------------------------------------------------------

def remove_old_files(directory, keep_count):
    """
    Keep only the newest N files in a directory; delete the rest.

    Files are sorted by last modified time (newest first). If the directory
    does not exist, the function logs and returns. Deletion errors are logged
    but not raised.
    """
    logging.info(f'Executing: remove_old_files')

    # Check if the target directory exists
    if not os.path.exists(directory):
        logging.info(f' - Directory {directory} not found.')
        return


    # List all files in the directory
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    # Sort the files by modified time, newest first
    files.sort(key=os.path.getmtime, reverse=True)

    # Determine files to delete
    files_to_delete = files[keep_count:]
    # Delete the older files
    for file in files_to_delete:
        try:
            os.remove(file)
            logging.info(f' - Deleted file: {file}')
        except Exception as e:
            logging.info(f' - Error deleting file {file}: {e}')
    
    
