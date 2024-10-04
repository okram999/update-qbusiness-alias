# Update user alias for qbusiness application

The logic is get the list of email ids that are in both the AWS IDC group (enabled to access the qbusiness app) and the confluence-user group. This list will represent the actual list of users that should have access to qbusiness app and then to the data from Confluence. We will then use this list to create an alias in qbusiness using the `lowercased` email id from Confluence.

For a userid to be found during the qbusiness's `get_user` api, they should have signed-in atleast once in qbusiness app. 
