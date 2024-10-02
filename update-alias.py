import boto3
import pandas as pd
import json

# Variables
# aws identity center id
idc_id='d-9067f63f1d'
# aws identity center group id. This is where all the group used to provision access for CLIO/CLI's qbusiness app
group_id='c4f82438-40a1-7012-f71a-8ce3a560af3c'
# aws qbusiness application id. 
qbusiness_app_id='760ec35b-fb8b-412a-9705-acd5b3ae3b96'
# aws account id with qbusiness deployed
aws_account_id='xxxxxxxxxx'
# control tower roles to be used from the management account. This is to interact with the qbusiness app
control_tower_role=f'arn:aws:iam::{aws_account_id}:role/AWSControlTowerExecution'


# boto3 clients
client = boto3.client('identitystore')
sts_client = boto3.client('sts')

# function to generate temp credentials in the qbusiness account
def assume_role(role_arn, RoleSessionName='qbussiness-session'):
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=RoleSessionName
    )
    new_session = boto3.Session(aws_access_key_id=response['Credentials']['AccessKeyId'],
                      aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                      aws_session_token=response['Credentials']['SessionToken'])
    return new_session


# function to get a list of UserId from a group in IDC
def get_users_from_group(group_id):
    users = []
    response = client.list_group_memberships(
        IdentityStoreId=idc_id,
        GroupId=group_id,
        MaxResults=100
    )
    for user in response['GroupMemberships']:
        users.append(user['MemberId']['UserId'])
    return users

# function to get the email address of a user from IDC
def get_user_email(user_id):
    response = client.describe_user(
        IdentityStoreId=idc_id,
        UserId=user_id
    )
    emails = response['Emails']
    primary_email = next((email['Value'] for email in emails if email['Primary']), None)
    return primary_email

# loop through the list of user_id and return the email address in lower case from AWS IDC
def get_user_emails(user_id_list):
    idc_emails = []
    for user_id in user_id_list:
        idc_emails.append(get_user_email(user_id))
    # Convert all elements to lowercase in-place
    idc_emails[:] = [email.lower() for email in idc_emails]
    return idc_emails

def qbusiness_update_user(email, qbusiness_app_id):
    qbusiness_client = assume_role(control_tower_role).client('qbusiness')
    response = qbusiness_client.update_user(
        applicationId=qbusiness_app_id, 
        userId=email,
        userAliasesToUpdate=[
            {
                'userId': email
            },
        ]
    )
    print(f"User {email} updated in qbusiness. Response is {response['userAliasesUpdated']}")


# Extract the user emails in confluence via the exported .CSV
# The file must be the root of this folder
df = pd.read_csv('export-users.csv')
column_name = 'email'
# Convert the column to a list
confluence_email_list = df[column_name].tolist()
# Print the list to verify
print(f"List of user email ids in confluence: {confluence_email_list}")

qbusiness_client = assume_role(control_tower_role).client('qbusiness')

# main handler function for aws lambda
def lambda_handler(event, context):
    user_id_list = get_users_from_group(group_id)
    idc_user_emails = get_user_emails(user_id_list)
    print(f"List of lowercased user email ids from aws idc: {idc_user_emails}")

    user_not_in_confluence = []
    user_not_in_qbusiness = []
    user_in_both_but_failed_to_process = []

# check if a user in the AWS IDC group exist in confluence-users group
# if yes, check if the user exists in qbusiness
# if the user exists in qbusiness, update the user alias in qbusiness to use the all lowercased email from confluence
# if the user does not exist in qbusiness, add the user to user_not_in_qbusiness list. This could mean the user have never log-in to qbusiness application.
# if the user is not in confluence, add the user to user_not_in_confluence list
# if the user is in both but failed to process, add the user to user_in_both_but_failed_to_process list
    print("Checking user emails in confluence against qbusiness")
    for email in idc_user_emails:
        if email in confluence_email_list:
            # check if a user object was created in qbusiness
            try:
                print(f"Checking if user {email} exists in qbusiness")
                response = qbusiness_client.get_user(applicationId=qbusiness_app_id, userId=email)
                print(response)
                # If successful, do something with the response
                print(f"User {email} exists in qbusiness")
                # create an alias in qbusiness
                qbusiness_update_user(email, qbusiness_app_id)
            except qbusiness_client.exceptions.ResourceNotFoundException:
                print(f"User {email} not found in qbusiness appliction, adding it to user_not_in_qbusiness list")
                user_not_in_qbusiness.append(email)
            except Exception as e:
                print(f"An error occurred while processing {email}: {str(e)}")
                user_in_both_but_failed_to_process.append(email)
                print(f"User {email} is in both AWS IDC and Confluence groups, but failed to process, adding it to user_in_both_but_failed_to_process list")
                continue  # This will skip to the next email in the loop

        else:
            print(f"{email} is not in the confluence list, adding it to user_not_in_confluence list")
            user_not_in_confluence.append(email)

    print(f"User not in confluence: {user_not_in_confluence}")
    print(f"User not in qbusiness: {user_not_in_qbusiness}")
    print(f"User in both but failed to process: {user_in_both_but_failed_to_process}")

    return {
        'statusCode': 200,
        'body': json.dumps('Execution completed successfully')
    }


# test invoking the lambda function
if __name__ == '__main__':
    lambda_handler(None, None)

