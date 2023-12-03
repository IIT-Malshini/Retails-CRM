
# -------------------------- compulsory libraries --------------------------

import boto3
import json
import argparse
import snowflake.connector
from botocore.exceptions import ClientError

# -------------------------- define your libraries here --------------------------

import pandas
import os
import pytz
from datetime import datetime
import sys
import copy
from pprint import pprint


########################### Get Configuration Function ###########################

print("import the getJsonData function")

def getJsonData(bucket_name,key_name):
    '''
    this will pick the json config file from s3 bucket
    '''
    
    s3_client = boto3.client('s3')
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=key_name)
    body = csv_obj['Body']
    
    json_string = body.read().decode('utf-8')
    json_content = json.loads(json_string)
    
    return json_content

print("json script loaded successfully")

######################### Define Other Required Functions ########################

def get_secret(secret_name,region_name):

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    secret = None

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
       
    return secret

def createSnowflakeConnection(snowflake_secret):
    data = get_secret(snowflake_secret['secret_name'],snowflake_secret['region'])
    
    if data is not None:
        data = json.loads(data);
        #print(data)
        snuser = data.get('snowflake_user')
        password = data.get('snowflake_password')
        account = data.get('snowflake_account')
        #wh = snowflake_secret['wh_name']
        wh = data.get('snowflake_warehouse')
        db = data.get('snowflake_database')
        conn = snowflake.connector.connect(
            user=snuser,
            password=password,
            account=account,
            warehouse=wh,
            database=db
            #schema=schema
        )
    else:
        print("snowflake Secret manager return None.")
    return conn

class DataProvisioningException(Exception):
    """
    INFO: This Exception is raised when there are problems related to
    1. Insufficient data which is checked by PRECHECK SP in Snowflake
    2. Undefined SP is being called / executed
    3. Generic Error caused due to passed params or other python related logic
    """
    pass


def parse_args():
    
    '''
    this will pass the arguments from the pipeline training file
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=['dev', 'uat', 'prod'])
    parser.add_argument("--project_prefix", required=True)
    parser.add_argument("--config_bucket_name", required=True)
    parser.add_argument("--config_key_name", required=True)
    
    return parser.parse_known_args()

def foo():
    pass

############################# Define Globle Variables ############################




############################### Code For The Script ##############################

if __name__ == "__main__":
    
    ########## Pipeline Variables ###########
    
    args, _ = parse_args()
    
    env = args.env
    project_prefix = args.project_prefix
    config_bucket_name = args.config_bucket_name
    config_key_name = args.config_key_name
    config = getJsonData(config_bucket_name,config_key_name)
    
    ########### Define Variables ############
    
#     database = config['SnowflakeSpecific']['Database']
#     schema = config['SnowflakeSpecific']['Schema']
#     snowflake_secret_name = config['SnowflakeSpecific']['SnowflakeSecretName']
    
    
    
    ########## Code For The Step ###########
    
    snowflake_secret = {}
    snowflake_secret['secret_name'] = 'snowflake-nonpii-access-common-dev'
    snowflake_secret['region'] = 'ap-southeast-1'
    
    srilank_tz = pytz.timezone("Asia/Colombo")
    exe_id = datetime.now(srilank_tz).strftime("%Y%m%dT %H%M%S")
    load_ts = datetime.now(srilank_tz).strftime("%Y-%m-%d %H:%M:%S")
    print (load_ts)
    
    try:
        ctx = createSnowflakeConnection(snowflake_secret)
    except:
        print("Unable to Connect to Snowflake")
        raise
                        
    output = ''

    
########################################################################

    print("--------------- Proc 1 started ---------------")
#     sp_name = None  # ex: config['SnowflakeSpecific']['SnowflakeProc4']
    
#     writeJSON = {"etl_name": "CHANNEL PLANNING GROSSADSQT",    # Example for 'DTV_POP Churn'. Change according to the project
#                    "etl_task_name": "ML CHANNEL PLANNING GROSSADSQT Postprocess",
#                    "executed_sp":"COMMON_USER_CHANPLAN.ML_CHANNELPLANNING_GROSSADSQT_PROC",
#                    "uploaded_date": load_ts,
#                    "load_date":load_ts,
#                    "execution_id": "CHANNEL_PLANNING_GROSSADSQT-"+load_ts}
#     writeDict=json.dumps(writeJSON)
    
    
    try:
        cs=ctx.cursor()
        cs.execute(f"use schema COMMON_USER_ANALYTICS")
        print ("Starting to execute procedure")
#         cursor=cs.execute(f'''call LOAD_WEBSCRAPED_FOOD_SHOP_DETAILS_PROC(
#                             array_construct(
#                                 'WEBSITE',
#                                 'CATEGORY',
#                                 'SHOP_NAME',
#                                 'MOBILE_NUMBER_1',
#                                 'MOBILE_NUMBER_2',
#                                 'DATE'))''')

        cursor=cs.execute(f"""call common_user_analytics.LOAD_WEBSCRAPED_FOOD_SHOP_DETAILS_PROC()""")
        print("proc ran completed")
        
        if not cursor:
            raise Exception
        
        for col in cursor:
            #output = col
            print(col)
            
#         if "Success" in output[0]:
#             print (output[0]) 
#         elif "Failed" or "Error" in output[0]:
#             print (output[0])
#             sys.exit(1)
        
        cursor.close()

 ########################################################################################################
        
    except Exception as e: 
        print(f"Exception: {e}")
        sys.exit(1)