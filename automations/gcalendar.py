import pandas as pd
import os, datetime
from flask import Flask, request, g, session

import pymongo

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.config.from_object('config.Config')

class CalendarWrapper(object):

    def __init__(self, cred_location=None, gc=None, db:pymongo.database.Database=None) -> None:
        self.db = db
        self.creds = gc
        self.cred_location = cred_location
        
        self.scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.events.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.settings.readonly",
            'https://www.googleapis.com/auth/drive'
        ]
        
        if os.path.exists(self.cred_location) and not self.creds:
            self.creds = Credentials.from_service_account_file(self.cred_location, scopes=self.scopes)
            
        self.service = build('calendar', 'v3', credentials=self.creds)

    def create_creds(self):
        scopes = self.scopes
        if os.path.exists(self.cred_location) and not self.creds:
            self.creds = Credentials.from_service_account_file(self.cred_location, scopes=scopes)
        return self.creds
    
    def init_service(self):
        creds = self.create_creds()
        self.service = build('calendar', 'v3', credentials=self.creds)
        
    def insert_calendar(self, id="uicpdshared@gmail.com"):
        calendar_list_entry = {
            'id': id
        }
        created_calendar_list_entry = self.service.calendarList().insert(body=calendar_list_entry).execute()
        app.logger.info("Added calendar: ", created_calendar_list_entry['summary'])
            
    def list_calendars(self):
        page_token = None
        while True:
            calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
            app.logger.info(calendar_list)
            for calendar_list_entry in calendar_list['items']:
                app.logger.info(calendar_list_entry['summary'])
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
            
    def get_events(self, id):
        page_token = None
        while True:
            events = self.service.events().list(calendarId=id, pageToken=page_token).execute()
            for event in events['items']:
                # self.db.events.insert_one(event)
                ret = self.db.events.find_one_and_replace(
                    {
                        'updated': {'$eq': str(event['updated'])},
                        'summary': {'$eq': str(event['summary'])}
                    }, 
                    event,
                    upsert=True,
                    return_document=pymongo.ReturnDocument.AFTER
                )
                app.logger.info("Inserted event: {0} {1} {2}".format(
                    ret['updated'],
                    ret['summary'],
                    ret['description']
                ))
                # try:
                #     event['updated'] = str(event['updated'])
                #     event['summary'] = str(event['summary'])
                #     self.db.events.insert_one(event)
                # except pymongo.errors.DuplicateKeyError as e:
                #     duplicate_warning = "Existing event found, replacing: "
                #     self.db.events.find_one_and_replace(
                #         {
                #             'updated': {'$eq': str(event['updated'])},
                #             'summary': {'$eq': str(event['summary'])}
                #         }, 
                #         event
                #     )
                #     app.logger.warning("{0} {1} {2}".format(duplicate_warning,
                #                                             event['updated'],
                #                                             event['summary']))
            page_token = events.get('nextPageToken')
            if not page_token:
                break

    def get_calendar(self):
        try:
            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            app.logger.info('Getting the upcoming 10 events')
            events_result = self.service.events().list(calendarId='primary',
                                                       timeMax=now,
                                                       maxResults=10,
                                                       singleEvents=True,
                                                       orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                app.logger.info('No upcoming events found.')
                return

            # Logs the start and name of the next 10 events
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                app.logger.info(start, event['summary'])

        except HttpError as error:
            app.logger.info('An error occurred: %s' % error)
