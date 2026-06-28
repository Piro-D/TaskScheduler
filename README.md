# Project Description
This is a Machine Learning Project made by 3 people :
- Jason Nicholas Rahardjo - 2802411411
- Arnaldo Setiawan - 2802410232
- Antonius Steven - 2802415870

There are 3 branches for deployment, one for local deployment, and the other for azure cloud deployment.
- main -> Azure Cloud Deployment
- API_Based_LLM_Local_Deployment -> Local Deployment (recommended for testing)
- RM_Local_Model -> Local Model LLM using Ollama
To change branches in VScode, please go to the bottom left of VScode, and change the selected branch to the target branch.

### This branch supports local deployment only. The following steps explain how to run the project on your machine.

Note for MLFlow code:
- Due to dependency conflicts, ML flow needs to be manually installed through the terminal ("pip install mlflow")
- The ML Flow code is stored inside duration_estimator.py, uncomment it if you want to run and produce the artifacts
- MLFlow artifacts are named ml_runs.zip and mlflow.db



# Project Structure

- app.py Flask routes and request orchestration
- config.py Shared paths and app settings
- services/ Calendar, OAuth, upload, and saved-state helpers
- ml/ LLM decomposition and duration-estimation pipeline + preprocessing file
- templates/ Flask/Jinja pages
- static/ CSS and browser assets
- Datasets/ Source training data
- TestDocuments/ Local sample documents
- instance/ Ignored runtime schedule state
- artifacts/ Ignored generated CSV/JSON outputs
- uploads/ Ignored temporary uploaded files
- models/ Ignored local model files



# Local Deployment Guide

For local deployment, there are 2 things we need to do. 
- First is project intialization
- Second is API setup (Google calendar & Groq)


## Project Initialization

1. Create a virtual environment ( 'python -m venv .venv' )

2. Activate the virtual environment ( '.venv\Scripts\Activate.ps1' )

3. Install Python Dependencies ( 'pip install -r requirements.txt' )

4. Create the Environment File (.env) and paste the following template to it
- FLASK_SECRET_KEY=local_testing_secret_key
- FLASK_ENV=development
- GOOGLE_CLIENT_ID=
- GOOGLE_CLIENT_SECRET=
- GROQ_API_KEY=
(Note: Setting FLASK_ENV=development enables local HTTP redirects for Google OAuth.)

5. These .env fields will be filled in the API setup stage

6. Generate the preprocessed dataset ( 'python -m ml.preprocess' )

7. Train the duration estimation model ( 'python -m ml.duration_estimator' )

9. Run the Flask server ('python app.py')

10. Log in: Open http://localhost:8080 in your browser. Log in using the test Google account.

11. Test the Pipeline: Submit any project documents (Sample documents are already included in the .\TestDocuments folder).


## API Setup

### API Setup 1: Groq API Initialization (Replaces Ollama)

1. Go to the Groq Cloud Console (Link: https://console.groq.com/).

2. Create an account or log in.

3. On the left sidebar, go to API Keys.

4. Click Create API Key.

5. Copy the generated key and paste it next to GROQ_API_KEY= in your .env file.


### API Setup 2: Google OAuth Credentials

1. Go to Google Cloud Console (Link: https://console.cloud.google.com/home).

2. Next to the Google Cloud logo in the top left, select the project dropdown and Create a New Project.

3. Click the top left hamburger menu, go to APIs & Services > Library. Search for Google Calendar API and click Enable.

4. Go back to the top left menu, and select APIs & Services > OAuth consent screen.

4. After this, configure the Google Auth Platform by clicking Get Started.

5. Select External as the User Type and click Create.

6. Fill in the required app information (App name, support email, developer email) and click Save and Continue through the Scopes phase.

7. Next go to Audience and under the Test Users phase, click Add Users. Add the specific Gmail address you intend to test the app with, then click Save.

8. Now go to APIs & Services > Credentials on the left sidebar.

9. Click Create Credentials at the top, and select OAuth Client ID.

10. Under Application type, select Web application and name it "Flask Local Client".

11. Scroll down to Authorized redirect URIs, click Add URI, and paste this exact URL: http://localhost:8080/oauth2callback

12. Click Create.

13. Copy your Client ID and paste it next to GOOGLE_CLIENT_ID= in your .env file.

14. Copy your Client Secret and paste it next to GOOGLE_CLIENT_SECRET= in your .env file.

