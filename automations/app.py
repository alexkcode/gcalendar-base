import os, secrets
from multiprocessing import Process, Queue
from datetime import datetime
import pytz
from pytz import timezone

from google.oauth2.service_account import Credentials

import pymongo

import logging
import config, gcalendar

import flask
from flask import Flask, request, g, session, render_template, redirect
import apscheduler, atexit
from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
app.config.from_object('config.Config')

# class Formatter(logging.Formatter):
#     """override logging.Formatter to use an aware datetime object"""

#     def converter(self, timestamp):
#         # Create datetime in UTC
#         dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
#         # Change datetime's timezone
#         return dt.astimezone(pytz.timezone('America/New_York'))
        
#     def formatTime(self, record, datefmt=None):
#         dt = self.converter(record.created)
#         if datefmt:
#             s = dt.strftime(datefmt)
#         else:
#             try:
#                 s = dt.isoformat(timespec='milliseconds')
#             except TypeError:
#                 s = dt.isoformat()
#         return s

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
fh = logging.handlers.TimedRotatingFileHandler('error.log', when='D', interval=1)
# fh.setFormatter(Formatter('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) -35s %(lineno) -5d: %(message)s', '%m-%d-%y %H:%M:%S'))
logging.basicConfig(
    level=logging.INFO, 
    format=LOG_FORMAT,
    # datefmt='%m-%d-%y %H:%M:%S %I:%M:%S %p',
    datefmt='%m-%d-%y %I:%M:%S %p',
    handlers=[fh]
)

def get_scheduler():
    if not 'scheduler' in g:
        g.scheduler = BackgroundScheduler()
    return g.scheduler

def get_follower_job_queue():
    if not 'follower_job_queue' in g:
        g.follower_job_queue = Queue()
    return g.follower_job_queue

def get_mongo_db():
    if not 'db' in g:
        # these parameters are fixed in the docker-compose
        g.db_client = pymongo.MongoClient('mongodb', 27017)
        g.db = g.db_client['gcalendar']
        # g.db.events.create_index(
        #     [
        #         ('updated', pymongo.DESCENDING),
        #         ('summary', pymongo.ASCENDING)
        #     ],
        #     unique=True
        # )
    return g.db

def get_gc():
    scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.events.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.settings.readonly",
            'https://www.googleapis.com/auth/drive'
    ]
    
    if not 'gc' in g:
        g.gc = Credentials.from_service_account_file(app.config['CRED_LOCATION'], 
                                                     scopes=scopes)
    return g.gc

def get_calw():
    if not 'calw' in g:
        g.calw = gcalendar.CalendarWrapper(cred_location=app.config['CRED_LOCATION'],
                                           db=get_mongo_db())
    return g.calw

scheduler = None
with app.app_context():
    scheduler = get_scheduler()

@app.before_request
def before_request():
    # g.db = get_db()
    app.config.from_object('config.Config')

@app.route("/download_calendar/calendar_id=<calendar_id>")
def download_calendar(calendar_id):
    try:
        app.logger.warning("STARTING GOOGLE CALENDAR DOWNLOAD")
        with app.app_context():
            calw = get_calw()
            calw.upsert_all_events(calendar_id)
    except Exception as e:
        app.logger.error("GOOGLE CALENDAR DOWNLOAD FAILED at {0}".format(datetime.now()))
        raise(e)
    else:
        success_message = "GOOGLE CALENDAR DOWNLOAD SUCCEEDED"
        app.logger.warning(success_message)
        return success_message

@app.route("/start_scheduler/", methods = ['GET', 'POST'])
def start_scheduler(calendar_id, interval=120):
    try:
        calendar_id = request.args.get("calendar_id")
        interval = request.args.get("interval")
    except Exception as e:
        with app.app_context():
            warning = """
                No request arguments found for calendar_id or interval, 
                passing parameters to download_calendar method.\n
            """
            app.logger.warning(warning, e)
    try:
        scheduler.start(paused=False)
        scheduler.add_job(
            func=download_calendar, 
            kwargs={"calendar_id": calendar_id},
            trigger="interval", 
            seconds=interval,
            start_date=datetime.now()
        )
    except Exception as e:
        with app.app_context():
            app.logger.error(e)
    finally:
        return "JOB SCHEDULER RESTARTED"

@app.route("/stop_scheduler")
def stop_all():
    try:
        scheduler.shutdown()
    except Exception as e:
        return "NO JOBS TO DELETE.\n{0}".format(e)
    else:    
        return "ALL JOBS STOPPED AND DELETED. JOB SCHEDULER HAS STOPPED."

# scheduler.add_job(
#     func=download_calendar, 
#     trigger="interval", 
#     seconds=30,
#     start_date=datetime.now()
# )
# scheduler.start(paused=True)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form['submit_button'] == 'STOP ALL JOBS':
            return stop_all()
        if request.form['submit_button'] == 'CURRENT JOBS':
            jobs = []
            try:
                # return list of current jobs
                pass
            except Exception as e:
                app.logger.error('Error when checking current jobs: {0}'.format(e))
            return 'Current jobs: {0}'.format(jobs)
    # return render_template('index.html')
    return "OK"

# atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=False)