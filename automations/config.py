from flask import Flask, request, redirect, Response, logging, g
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

class Config(object):
    EMAIL1 = os.getenv('EMAIL1')
    EMAIL2 = os.getenv('EMAIL2')
    # make sure to update this!
    CRED_LOCATION = 'service_account_token.json'
    CONFIG_LOCATION = 'config.json'

    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.settings.readonly",
        'https://www.googleapis.com/auth/drive'
    ]