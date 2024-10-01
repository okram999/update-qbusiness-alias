# for each email in the export-users.csv, we need to perform the below:
# 1. create an alias in the users table of amazon qbusiness
# 2. handle any errors that may occur and continue till all the emails are processed


#!/bin/bash

# Replace 'your_file.csv' with the actual file path
file="export-users.csv"
app_id="your_app_id"
region="us-east-1"
column_index=2  # Replace with the index of the column you want (starting from 0)

# Read the file line by line
while IFS=',' read -ra line; do
  # Access the specific column value
  user_email_id="${line[$column_index]}"

  # if the user already exists in the qbusiness database, then we need to update the alias.
  # the command to check is  aws qbusiness get-user --application-id <value> --user-id <user_email>
  # if user exists, then update the alias. The command to update alias is: aws qbusiness update-user --application-id <app_id> --region <region> --user-id <user_email for user from IAM Identity Center> --user-aliases-to-update='[{"userId": "<user_id that was synced in ACLs from data source>"}]'
  # else, handle user not found and continue
  # echo "User not found: $user_email_id"
  # continue
  # Add your logic here to handle the user
  echo "Processing user: $user_email_id"
  aws qbusiness get-user --application-id $app_id --user-id $user_email_id
  if [ $? -eq 0 ]; then
    aws qbusiness update-user --application-id $app_id --region $region --user-id $user_email_id --user-aliases-to-update='[{"userId": "$user_email_id"}]

  echo "$user_email_id"

done < "$file"