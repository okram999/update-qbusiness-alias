# Update user alias for qbusiness application

The logic is get the list of email ids that are in both the AWS IDC group (enabled to access the qbusiness app) and the confluence-user group. This list will represent the actual list of users that should have access to qbusiness app and then to the data from Confluence. We will then use this list to create an alias in qbusiness using the `lowercased` email id from Confluence.

For a userid to be found during the qbusiness's `get_user` api, they should have signed-in atleast once in qbusiness app. 


# Setting up the execution environment

We can run this script for a local laptop's terminal. You should make sure you set the temp credentials from the management account as env variables. Use AWS SSO console to get the temp credentials. Update the variables in the scrip to match your environment e.g. the idc id, idc group id, target aws account id, etc. Also make sure the confluence user export `.csv` file in the same directory. Thats all we need. Once set execute the python script.
