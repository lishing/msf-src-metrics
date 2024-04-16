import streamlit_authenticator as stauth
import yaml
import streamlit as st

# def authenticate_user():
with open('config.yaml') as file:
    config = yaml.safe_load(file)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)
# Prompt user for email and password
name, authentication_status, username = authenticator.login()

if authentication_status:
    authenticator.logout()
    st.title('Some contents') # should be replaced by main contents on app.py
elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')