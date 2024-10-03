import boto3
import pandas as pd
import json

# Variables
# aws identity center id
idc_id = "d-9067f63f1d"
# aws identity center group id. This is where all the group used to provision access for CLIO/CLI's qbusiness app
group_id = "c4f82438-40a1-7012-f71a-8ce3a560af3c"
# aws qbusiness application id.
qbusiness_app_id = "760ec35b-fb8b-412a-9705-acd5b3ae3b96"
# aws account id with qbusiness deployed
aws_account_id = "xxxxxxxx"
# control tower roles to be used from the management account. This is to interact with the qbusiness app
control_tower_role = f"arn:aws:iam::{aws_account_id}:role/AWSControlTowerExecution"


# boto3 clients
client = boto3.client("identitystore")
sts_client = boto3.client("sts")


# function to generate temp credentials in the qbusiness account
def assume_role(role_arn, RoleSessionName="qbussiness-session"):
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=RoleSessionName)
    new_session = boto3.Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )
    return new_session


# function to get a list of UserId from a group in IDC
def get_users_from_group(group_id, idc_id):
    paginator = client.get_paginator("list_group_memberships")

    for page in paginator.paginate(IdentityStoreId=idc_id, GroupId=group_id):
        yield from (user["MemberId"]["UserId"] for user in page["GroupMemberships"])


# function to get the email address of a user from IDC
def get_user_email(user_id, idc_id):
    response = client.describe_user(IdentityStoreId=idc_id, UserId=user_id)
    emails = response["Emails"]
    primary_email = next((email["Value"] for email in emails if email["Primary"]), None)
    return primary_email


# loop through the list of user_id and return the email address in lower case from AWS IDC
def get_user_emails(user_id_list, idc_id):
    idc_emails = []
    for user_id in user_id_list:
        idc_emails.append(get_user_email(user_id, idc_id))
    return idc_emails


# function to create an alias in qbusiness app
def qbusiness_update_user(email, qbusiness_app_id):
    qbusiness_client = assume_role(control_tower_role).client("qbusiness")
    response = qbusiness_client.update_user(
        applicationId=qbusiness_app_id,
        userId=email,
        userAliasesToUpdate=[
            {"userId": email.lower()},
        ],
    )
    print(
        f"User {email} updated in qbusiness. Response is {response['userAliasesUpdated']}"
    )


# Get a list of emails that exist in the IDC group and confluence-user group
# but return the orginal email format from the IDC
def find_common_emails(emailList, emailListLowerCase):
    commonEmails = []
    for email in emailList:
        if email.lower() in emailListLowerCase:
            commonEmails.append(email)
    return commonEmails


# Extract the user emails in confluence via the exported .CSV
# The file must be the root of this folder
def get_confluence_user_emails(file):
    df = pd.read_csv(file)
    column_name = "email"
    # Convert the column to a list
    confluence_email_list = df[column_name].tolist()
    return confluence_email_list


# qbusiness client with cross account session
qbusiness_client = assume_role(control_tower_role).client("qbusiness")


# main handler function for aws lambda
def lambda_handler(event, context):

    # get the list of user emails id from IDC
    user_id_list = list(get_users_from_group(group_id, idc_id))
    idc_user_emails = get_user_emails(user_id_list, idc_id)

    # get the list of user emails id from confluence's user export .csv file
    confluence_user_emails = get_confluence_user_emails("export-users.csv")

    # email ids in both idc and confluence
    actual_qbusiness_users = find_common_emails(idc_user_emails, confluence_user_emails)
    print(
        f"User found in both AWS IDC group and Confluence group: {actual_qbusiness_users}"
    )

    # empty list for collecting data
    user_not_in_qbusiness = []
    user_in_both_but_failed_to_process = []

    for email in actual_qbusiness_users:
        try:
            print(f"Checking if user {email} exists in qbusiness")
            response = qbusiness_client.get_user(
                applicationId=qbusiness_app_id, userId=email
            )
            print(response)
            # If successful, do something with the response
            print(f"User {email} exists in qbusiness")
            # create an alias in qbusiness
            qbusiness_update_user(email, qbusiness_app_id)
        except qbusiness_client.exceptions.ResourceNotFoundException:
            print(
                f"User {email} not found in qbusiness appliction, adding it to user_not_in_qbusiness list"
            )
            user_not_in_qbusiness.append(email)
        except Exception as e:
            print(f"An error occurred while processing {email}: {str(e)}")
            user_in_both_but_failed_to_process.append(email)
            print(
                f"User {email} is in both AWS IDC and Confluence groups, but failed to process, adding it to user_in_both_but_failed_to_process list"
            )
            continue

    print(
        f"User in IDC and confluence export but not in qbusiness: {user_not_in_qbusiness}"
    )
    print(
        f"User in IDC and confluence export but failed to process: {user_in_both_but_failed_to_process}"
    )

    return {"statusCode": 200, "body": json.dumps("Execution completed successfully")}


# test invoking the lambda function
if __name__ == "__main__":
    lambda_handler(None, None)
