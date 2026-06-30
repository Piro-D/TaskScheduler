# Project Description

There are 3 branches for deployment, one for local deployment, and the other for azure cloud deployment.
- main -> Azure Cloud Deployment
- API_Based_LLM_Local_Deployment -> Local Deployment (recommended for testing)
- RM_Local_Model -> Local Model LLM using Ollama
To change branches in VScode, please go to the bottom left of VScode, and change the selected branch to the target branch.

### This branch supports Azure cloud deployment only. The following steps explain how to run the project on Azure.

Note for MLFlow code:
- Due to dependency conflicts, ML flow needs to be manually installed through the terminal ("pip install mlflow")
- The ML Flow code is stored inside duration_estimator.py, uncomment it if you want to run and produce the artifacts
- MLFlow artifacts are named ml_runs.zip and mlflow.db


# API Setup
Before deploying, we need to first setup the Groq API and the google calendar API.

## Groq API setup

1. Go to the Groq Cloud Console (Link: https://console.groq.com/).

2. Create an account or log in.

3. On the left sidebar, go to API Keys.

4. Click Create API Key.

5. Copy the generated key and keep it saved GROQ_API_KEY

## Google Calendar API Setup

1. Go to Google Cloud Console (Link: https://console.cloud.google.com/home).

2. Next to the Google Cloud logo in the top left, select the project dropdown and Create a New Project.

3. Click the top left hamburger menu, go to APIs & Services > Library. Search for Google Calendar API and click Enable.

4. Go back to the top left menu, and select APIs & Services > OAuth consent screen.

5. After this, configure the Google Auth Platform by clicking Get Started.

6. Select External as the User Type and click Create.

7. Fill in the required app information (App name, support email, developer email) and click Save and Continue through the Scopes phase.

8. Next go to Audience and under the Test Users phase, click Add Users. Add the specific Gmail address you intend to test the app with, then click Save.

9. Now go to APIs & Services > Credentials on the left sidebar.

10. Click Create Credentials at the top, and select OAuth Client ID.

11. Under Application type, select Web application and name it "Flask Local Client".

12. For Authorized redirect URIs, we will later add an URL after creating the azure deployment. (Note : Very important step to ensure the system works)

13. Click Create.

14. Copy your Client ID and save it.

15. Copy your Client Secret and save it.





# ML Task-Scheduler: Azure Deployment Guide


## 1. Provision the Azure Infrastructure

The application runs on a Linux container managed by Azure App Service.

Log into the Azure Portal. (https://portal.azure.com)

Create a new Web App with the following configuration:
- Publish: Code
- Runtime stack: Python 3.12
- Operating System: Linux
- Region: Select the region closest to the target user base (e.g., Southeast Asia).
- Pricing Plan: Select a plan that supports custom domains and continuous deployment (Basic/B1 or higher recommended for memory-intensive ML models).


## 2. Configure Environment Variables (App Settings)

Azure App Service injects environment variables securely through its App Settings panel. Do not commit .env files to the repository.

Navigate to your newly created Web App in the Azure Portal.

On the left sidebar, go to Settings > Environment variables.

Add the following key-value pairs:
- FLASK_SECRET_KEY: A secure, random string for Flask session management.
- FLASK_ENV: production
- GOOGLE_CLIENT_ID: The Client ID from your Google Cloud Console OAuth credentials.
- GOOGLE_CLIENT_SECRET: The Client Secret from your Google Cloud Console.
- GROQ_API_KEY: Your API key from the Groq Console.
Click Apply to save the settings.


## 3. Configure the Custom Startup Command

By default, Azure's load balancers may time out long-running AI inference requests. To prevent Gunicorn from prematurely dropping requests, a custom startup command is required.

On the left sidebar, navigate to Settings > Configuration > Stack Settings.

Locate the Startup Command field and enter the following:

Bash
gunicorn --bind=0.0.0.0 --timeout 600 app:app

Click Save.


## 4. Setup GitHub Integration & Deployment

Azure App Service features native integration with GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD).

On the left sidebar, navigate to Deployment > Deployment Center.

Under Source, select GitHub.

Authenticate your GitHub account if prompted.

Select the Organization, Repository, and the specific Branch you wish to deploy (e.g., azure-deployment).

Click Save.


## 5. Add deployed URL to Google Authorized Redirect URLs

1. Copy the URL of the deployed website from Overview -> Essentials -> Default Domain

2. Go back to Google Cloud Console (https://console.cloud.google.com/home)

3. On the left dropdown hamburger menu, go to 'APIs and services' > 'Credentials'

4. Click on the created OAuth 2.0 Client IDs named 'Flask Local Client'

5. Add the copied URL of the depolyed website with the following format. ('https://' + copied URL + '/oauth2callback') 
Example : 'https://taskschedulertest-f5djccawbzdpa4af.indonesiacentral-01.azurewebsites.net/oauth2callback'

6. Click Save and wait a moment after changing.


The deployed website should operate properly after following the steps.

Note : If any erros are experienced during login, make sure the google account used to login matches with the google account added in google cloud console, make sure the environment variables inserted in azure are correct, and the authorized redirect link is inserted with the proper format.
