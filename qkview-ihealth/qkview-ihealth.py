#!/usr/bin/env python

"""
Name : qkview-ihealth.py
Author : fadly.tabrani@gmail.com | fads@f5.com
Version: 1.0

This script creates a qkview file and uploads it to F5 iHealth. 
It reads api credentials from a file named ihealth.apitokens in its current path. 
Each credential is a line in the format [client_id]:[client_secret].
"""

import argparse
import os
import logging
import requests
import subprocess
from datetime import datetime
from requests.auth import HTTPBasicAuth

def create_qkview(file_name):
    """
    Creates a qkview file using the `qkview` command.

    Parameters:
        file_name (str): The name of the qkview file to be created.

    Returns:
        str: The path to the created qkview file.

    Raises:
        subprocess.CalledProcessError: If the qkview command fails.
    """
    logging.info('Creating qkview file: {}.'.format(file_name))
    cmd = ['nice', '-n', '19', 'qkview', '-f', file_name]  # Run the command with low priority
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        logging.info("Qkview file created successfully.")
        logging.debug("Command output: %s", output.decode('utf-8'))
        return os.path.join('/var/tmp', file_name)
    except subprocess.CalledProcessError as e:
        logging.error("Error creating qkview file: %s", e.output.decode('utf-8'))
        raise

def get_access_token(token_url, client_id, client_secret):
    """
    Gets a valid access token from the iHealth API.

    Parameters:
        token_url (str): The URL to request the access token from.
        client_id (str): The client ID for authentication.
        client_secret (str): The client secret for authentication.

    Returns:
        str: A valid access token if successful, None otherwise.
    """
    try:
        auth = HTTPBasicAuth(client_id, client_secret)
        data = {'grant_type': 'client_credentials', 'scope': 'ihealth'}
        response = requests.post(token_url, data=data, auth=auth)
        response.raise_for_status()

        access_token = response.json().get('access_token')
        if access_token:
            logging.info("Access token obtained successfully.")
            return access_token
        else:
            logging.error("Error: Access token not found in response.")
    except requests.HTTPError as http_err:
        logging.error("HTTP error occurred while obtaining access token: {0}".format(http_err))
    except requests.RequestException as req_err:
        logging.error("Error obtaining access token: {0}".format(req_err))
    except ValueError as val_err:
        logging.error("Error: Invalid response format: {0}".format(val_err))
    
    return None

def get_access_token_from_list(token_url, apikeys):
    """
    Attempts to obtain an access token using a list of API keys.

    This function iterates through the provided API keys in reverse order,
    attempting to obtain an access token from the given token URL. If a valid
    access token is obtained, it is returned immediately. If all API keys fail,
    an exception is raised.

    Parameters:
        token_url (str): The URL to request the access token from.
        apikeys (list of str): A list of API keys in the format 'client_id:client_secret'.

    Returns:
        str: A valid access token.

    Raises:
        Exception: If no valid access token could be obtained from any of the API keys.
    """
    logging.info('Obtaining access token from API keys.')
    
    for i, apikey in reversed(list(enumerate(apikeys))):
        client_id, client_secret = apikey.split(':')
        logging.info("Trying API key {0}/{1}".format(i, len(apikeys)))
        
        try:
            access_token = get_access_token(token_url, client_id, client_secret)
            if access_token:
                return access_token
        except:
            pass

    raise Exception('Unable to obtain a valid access token')

def get_api_keys(file_path):
    """
    Reads API keys from a specified file.

    Parameters:
        file_path (str): The path to the file containing API keys.

    Returns:
        list of str: A list of API keys read from the file.

    Raises:
        Exception: If there is an error reading the file.
    """
    logging.info('Reading API keys from file: {}'.format(file_path))
    
    try:
        with open(file_path, 'r') as file:
            api_keys = [line.strip() for line in file if line.strip()]
        logging.info('Successfully read {} API keys.'.format(len(api_keys)))
        return api_keys
    except Exception as error:
        logging.error('Error reading API tokens file: {}'.format(error))
        raise

def upload_qkview(url, file_path, access_token):
    """
    Uploads the qkview file to the iHealth API using curl.

    Parameters:
        url (str): The URL to which the qkview file will be uploaded.
        file_path (str): The path to the qkview file to be uploaded.
        access_token (str): The access token for authorization.

    Raises:
        subprocess.CalledProcessError: If the curl command fails.
    """
    logging.info('Uploading qkview file.')
    cmd = [
        'curl', '--location', url,
        '--header', 'Authorization: Bearer {}'.format(access_token),
        '--form', 'qkview=@{}'.format(file_path)
    ]
    
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)  # Execute the curl command
        logging.info("Qkview file uploaded successfully")
    except subprocess.CalledProcessError as e:
        logging.error("Error uploading qkview file: {}".format(e.output))
        raise

def main():
    """
    Main function to orchestrate the steps of the script.
    """
    parser = argparse.ArgumentParser(description="qkview-ihealth script")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Starting qkview-ihealth script.")

    TOKEN_URL = 'https://identity.account.f5.com/oauth2/ausp95ykc80HOU7SQ357/v1/token'
    UPLOAD_URL = 'https://ihealth2-api.f5.com/qkview-analyzer/api/qkviews?visible_in_gui=true'

    # Look for API keys file in current directory.
    APIKEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ihealth.apitokens')
    
    # Name qkview file based on timestamp, for example "20241230-1159.qkview".
    QKVIEW_FILENAME = datetime.now().strftime('%Y%m%d-%H%M') + '.qkview'
    
    try:
        # Obtain API keys from the file
        apikeys = get_api_keys(APIKEYS_FILE)
        
        # Get an access token from the list of API keys
        access_token = get_access_token_from_list(TOKEN_URL, apikeys)
        
        # Create a qkview file
        qkview_file = create_qkview(QKVIEW_FILENAME)
        
        # Upload the qkview file
        upload_qkview(UPLOAD_URL, qkview_file, access_token)
    
    except Exception as e:
        logging.error("Unexpected error occurred: {0}".format(e))
        exit(1)

if __name__ == '__main__':
    main()
