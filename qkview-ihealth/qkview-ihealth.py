#!/usr/bin/env python

"""
Name : qkview-ihealth.py
Author : fadly.tabrani@gmail.com | fads@f5.com
Version: 1.0

This script creates a qkview file and uploads it to F5 iHealth. 
It reads api credentials from a file named ihealth.apitokens in its current path. 
Each credential is a line in the format [client_id]:[client_secret].
"""

import os
import requests
import subprocess
from datetime import datetime
from requests.auth import HTTPBasicAuth

token_url = 'https://identity.account.f5.com/oauth2/ausp95ykc80HOU7SQ357/v1/token'
qkview_url = 'https://ihealth2-api.f5.com/qkview-analyzer/api/qkviews'
upload_url = qkview_url + '?visible_in_gui=true'

qkview_file = datetime.now().strftime('%Y%m%d-%H%M') + '.qkview'
apitokens_file = os.path.join(os.path.abspath(__file__), 'ihealth.apitokens')
access_token = ''

with open(apitokens_file, 'r') as _f:

    # Read the apitokens file from the bottom up.
    api_keys = _f.read().split()

for api_key in api_keys:

    # Extract the client id and secret, get access token.
    client_id, key = api_key.split(':')
    auth = requests.auth.HTTPBasicAuth(client_id, key)
    data = {'grant_type': 'client_credentials', 'scope': 'ihealth'}
    response = requests.post(token_url, data=data, auth=auth)

    # Break out once we have a valid token.
    if (response.status_code == 200) and response.json()['access_token']:
        access_token = response.json()['access_token']
        break

# Test access to the API before proceeding
response = requests.get(qkview_url,
                        headers={'Authorization': 'Bearer ' + access_token})
if response.status_code != 200:
    exit(1)

cmd = ['nice', '-n', '19', 'qkview', '-f', qkview_file]

# Exit immediately with error code 1 if qkview creation failed.
if subprocess.call(cmd) != 0:
    exit(1)

cmd = ['curl', '--location', upload_url, '--header', 'Authorization: Bearer ' + access_token,
       '--form', 'qkview=@"' + '/var/tmp/' + qkview_file + '"']

# Exit with curl return code.
exit(subprocess.call(cmd))
