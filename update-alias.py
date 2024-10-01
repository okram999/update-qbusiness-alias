import boto3
import pandas as pd
import json

idc_id='d-9067f63f1d'
group_id='c4f82438-40a1-7012-f71a-8ce3a560af3c'
qbusiness_app_id='XXXXXXXXXXXX'

# boto3 client for aws identity center
client = boto3.client('identitystore')
qbusiness_client = boto3.client('qbusiness')

# function to get a list of UserId from a group
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

# function to get the email address of a user
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


# Main logic starts here
user_id_list = get_users_from_group(group_id)
idc_user_emails = get_user_emails(user_id_list)
print(f"List of lowercased user email ids from aws idc: {idc_user_emails}")

user_not_in_confluence = []
user_not_in_qbusiness = []
user_in_both_but_failed_to_process = []

for email in idc_user_emails:
    if email in confluence_email_list:
        # check if a user object was created in qbusiness
        try:
            response = qbusiness_client.get_user(applicationId=qbusiness_app_id, userId=email)
            # If successful, do something with the response
            print(f"User {email} exists in qbusiness")
            # create an alias in qbusiness
            qbusiness_update_user(email, qbusiness_app_id)
        except qbusiness_client.exceptions.ResourceNotFoundException:
            print(f"User {email} not found in qbusiness, adding it to user_not_in_qbusiness list")
            user_not_in_qbusiness.append(email)
        except Exception as e:
            print(f"An error occurred while processing {email}: {str(e)}")
            user_in_both_but_failed_to_process.append(email)
            continue  # This will skip to the next email in the loop

    else:
        print(f"{email} is not in the confluence list, adding it to user_not_in_confluence list") 
        user_not_in_confluence.append(email)

print(f"User not in confluence: {user_not_in_confluence}")
print(f"User not in qbusiness: {user_not_in_qbusiness}")
print(f"User in both but failed to process: {user_in_both_but_failed_to_process}")


