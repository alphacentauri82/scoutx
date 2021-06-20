import nexmo
import twilio.rest
import json, ast
import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from google.oauth2 import id_token
# from google.auth.transport import requests
import google.auth.transport.requests
import requests
from requests.auth import HTTPBasicAuth
from os.path import join, dirname
from dotenv import load_dotenv
from env_flag import env_flag
import time
# For UTC ISOFORMAT CALCULATIONS - Nightscout use another isoformat so we use the next modules to
# convert propertly and get most exact calculations
from datetime import datetime
import calendar
# We are going to use this to create an individual Thread for our Job
from multiprocessing import Process
# We detect if the user press ctl+c to stop the application
# If this keys are pressed then stop schedule threaded task
import signal
# We will use this to get a unique identifier for the schedule process
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Init the flask App
app = Flask(__name__)

# Import Scout models for the app context
with app.app_context():
    import models
    from models import model, scouts, scout

# enable cors
cors = CORS(app)
# define secret_key to flask app to manage sessions
app.secret_key = b'su\xdb\xf2\x94hK\x81J\x8c\xf7\x1e\xfb\x81F\xf1'

# load environment
envpath = join(dirname(__file__), "./.env")
load_dotenv(envpath)

# Load communication client for global usage in server

if env_flag('USE_TWILIO'):
    client = twilio.rest.Client(os.getenv('TWILIO_ACCOUNT_SID'),
                                os.getenv('TWILIO_AUTH_TOKEN'))
else:  
    client = nexmo.Client(
        application_id=os.getenv('NEXMO_APPLICATION_ID'),
        private_key=os.getenv('NEXMO_PRIVATE_KEY').replace('\\n','\n')
    )

active_scouts = []

# Login Logic


def get_session(key):
    value = None
    if key in session:
        value = session[key]
    return value


@app.route('/', methods=['GET', 'POST'])
def home():
    # Create scouts instance
    nightscouts = scouts()
    if get_session("user") != None:
        if request.method == "POST":
            extra_contacts = request.form.getlist('extra_contacts[]')
            if request.form.get("cmd") == "new":
                nightscouts.add(scout(email=get_session("user")["email"], username=get_session("user")["username"], nightscout_api=request.form.get(
                    'nightscout_api'), phone=request.form.get('phone'), emerg_contact=request.form.get('emerg_contact'), extra_contacts=extra_contacts))
            else:
                nightscouts.update({u'nightscout_api': request.form.get('nightscout_api'), u'phone': request.form.get(
                    'phone'), u'emerg_contact': request.form.get('emerg_contact'), u'extra_contacts': extra_contacts}, request.form.get('id'))
        return render_template("home.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), user=get_session("user"), scout=nightscouts.get_by_email(get_session("user")["email"]))
    else:
##        print(os.getenv("SITE_URL"))
        return render_template("login.html", client_id=os.getenv("GOOGLE_CLIENT_ID"), site_url=os.getenv("SITE_URL"))

# get the token_id and if valid then create the server session for persistance login
@app.route('/login', methods=["POST"])
def login():
    try:
        token = request.form.get("idtoken")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        infoid = id_token.verify_oauth2_token(
            token, google.auth.transport.requests.Request(), client_id)
        if infoid['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        userid = infoid['sub']
        # Here is a good place to create the session
        session["user"] = {"userid": userid, "username": request.form.get(
            "username"), "email": request.form.get("email")}
        return userid
    except ValueError:
        return "Error"
        pass

# user logout
@app.route('/logout')
def logout():
    # Remove the session
    session.pop("user", None)
    return redirect(url_for('home', _external=True, _scheme='https'))


# handle the notifications when nightscout api is not sending new entries.
# when this mark is 1 the sms is sent, when the mark is equal to WAIT_AFTER_SMS_MARK the mark is restarted to 1
nightscout_failed_update_wait_mark = {}


def handle_nightscout_failed_update(to, api_url, username):
    global client
    global nightscout_failed_update_wait_mark
    if to not in nightscout_failed_update_wait_mark:
        nightscout_failed_update_wait_mark[to] = 1
    else:
        nightscout_failed_update_wait_mark[to] += 1

    if nightscout_failed_update_wait_mark[to] == 1:
        if not env_flag('USE_TWILIO'):
            response = requests.post(
                'https://api.nexmo.com/v0.1/messages',
                auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"),
                                   os.getenv("NEXMO_API_SECRET")),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "from": {
                        "type": "sms",
                        "number": os.getenv("NEXMO_NUMBER"),
                    },
                    "to": {
                        "type": "sms",
                        "number": to
                    },
                    "message": {
                        "content": {
                            "type": "text",
                            "text": "Dear {0} the nightscout api is not retrieving updated entries, please check your device or your service to solve any issues".format(username)
                        }
                    }
                }
            ).json()
        else:
            message = client.messages \
                .create(
                     body="Dear {0} the nightscout api is not retrieving updated entries, please check your device or your service to solve any issues".format(username),
                     from_=os.getenv("TWILIO_NUMBER"),
                     to=to
                 )
                        
    elif nightscout_failed_update_wait_mark[to] == int(os.getenv("WAIT_AFTER_SMS_MARK")):
        nightscout_failed_update_wait_mark[to] = 0


# handle the number of failed attempts to customer nightscout api. If the number of intents exceeds the
# limit then a sms is sent to the customer
nightscout_failed_pings = {}


def handle_nightscout_failed_pings(to, api_url, username):
    global client
    global nightscout_failed_pings
    if to not in nightscout_failed_pings:
        nightscout_failed_pings[to] = 1
    else:
        nightscout_failed_pings[to] += 1
    # print('Intent: {0} for {1}'.format(nightscout_failed_pings[to],to))
    if nightscout_failed_pings[to] == int(os.getenv("NIGHTSCOUT_FAILED_PING_SMS")):
        # Reset the variable
        nightscout_failed_pings[to] = 0
        
        if not env_flag('USE_TWILIO'):
            response = requests.post(
                'https://api.nexmo.com/v0.1/messages',
                auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"),
                                   os.getenv("NEXMO_API_SECRET")),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "from": {
                        "type": "sms",
                        "number": os.getenv("NEXMO_NUMBER"),
                    },
                    "to": {
                        "type": "sms",
                        "number": to
                    },
                    "message": {
                        "content": {
                            "type": "text",
                            "text": "Dear {0} the Nightscout api url: {1} is not responding, please check the service".format(username, api_url)
                        }
                    }
                }
            ).json()

            if "message_uuid" in response:
                return True
        else:
            message = client.messages \
                .create(
                     body="Dear {0} the Nightscout api url: {1} is not responding, please check the service".format(username, api_url),
                     from_=os.getenv("TWILIO_NUMBER"),
                     to=to
                 )

            if message.status != 'failed':
                return True
            
    return False


def sms_glucose_alert(to, username, glucose):
    global client

    if not env_flag('USE_TWILIO'):
        # We send our sms using the messages api not the sms api
        response = requests.post(
            'https://api.nexmo.com/v0.1/messages',
            auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"),
                               os.getenv("NEXMO_API_SECRET")),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "from": {
                    "type": "sms",
                    "number": os.getenv("NEXMO_NUMBER"),
                },
                "to": {
                    "type": "sms",
                    "number": to
                },
                "message": {
                    "content": {
                        "type": "text",
                        "text": "Alert {username} Blood Glucose is {glucose}".format(username=username, glucose=glucose)
                    }
                }
            }
        ).json()

        if "message_uuid" in response:
            return True
    else:
        message = client.messages \
            .create(
                 body="Alert {username} Blood Glucose is {glucose}".format(username=username, glucose=glucose),
                 from_=os.getenv("TWILIO_NUMBER"),
                 to=to
             )

        if message.status != 'failed':
            return True
        
    return False


last_call = {}


def call_glucose_alert(to, glucose):
    if to in last_call:
        if int(time.time()-last_call[to]) < int(os.getenv("WAIT_AFTER_CALL")):
            print("The number {0} was called recently.. Please wait a little longer: {1}".format(
                to, int(time.time()-last_call[to])))
            return False
    # print('Call {0} {1}'.format(to, glucose))
    last_call[to] = time.time()
    
    if not env_flag('USE_TWILIO'):
        # We make our call using the voice API
        response = client.create_call(
            {
                "to": [{
                    "type": "phone",
                    "number": to
                }],
                "from": {
                    "type": "phone",
                    "number": os.getenv('NEXMO_NUMBER')
                },
                "ncco": [
                    {
                        "action": "talk",
                        "text": "Alert Your Blood Glucose is {0}".format(glucose)
                    }
                ],
                "eventUrl": [
                    "{url_root}/webhooks/events".format(
                        url_root=os.getenv("SITE_URL"))
                ]
            }
        )
        
        if "uuid" in response:
            return True
    else:
        call = client.calls.create(
                        twiml='<Response><Say>Alert Your Blood Glucose is {0}</Say></Response>'.format(glucose),
                        to=to,
                        from_=os.getenv("TWILIO_NUMBER")
                    )

        if call.status != 'failed':
            return True
        
    return False


def sms_request_glucose_level_nexmo(args, glucose):
    global client

    args = ast.literal_eval(json.dumps(args))
    
    # Parse incoming values
    keyword = args['keyword'][0]
    to = args["msisdn"][0]
    response = None

    if keyword == "NIGHTSCOUT":
        # "msg" stores the response to be sent\
        msg = "Hey, the latest blood glucose level entry: {glucose}".format(glucose=glucose)

        response = requests.post(
        'https://api.nexmo.com/v0.1/messages',
        auth=HTTPBasicAuth(os.getenv("NEXMO_API_KEY"),
                            os.getenv("NEXMO_API_SECRET")),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json={
            "from": {
                "type": "sms",
                "number": os.getenv('NEXMO_NUMBER')
            },
            "to": {
                "type": "sms",
                "number": to
            },
            "message": {
                "content": {
                    "type": "text",
                    "text": msg
                }
            }
        }).json()

    if response is not None and "message_uuid" in response:
        return True
    else:
        return False


# Nexmo webhooks
@app.route('/webhooks/inbound-messages', methods=["POST"])
def inbound_sms():
    args = dict(request.form)

    if args.get('status'):
        return args['status']

    sms_request_glucose_level_nexmo(args, glucose)

    return "Message Received"


@app.route('/webhooks/events', methods=["POST", "GET"])
def events():
    global client
    global active_scouts
    global glucose

    req = request.get_json()
    # Create scouts instance
    nightscouts = scouts()
    print(req)
    if "status" in req:
        if req["status"] == "completed":
            phone = req["to"]
            # The next line is not recomended its functional but use the global active_scouts variable
            # This variable is updated by the daemon process.. that run in another context
            # Not the flask context, for that reason we are going to use firebase to get
            # fresh data
            # uscout = [active_scout for active_scout in active_scouts if active_scout['phone'] == phone]
            uscout = nightscouts.getby_personal_phone(phone)
            if uscout != None:
                entries = requests.get(uscout["nightscout_api"]).json()
                glucose = entries[0]['sgv']
                sms_glucose_alert(
                    uscout["emerg_contact"], uscout["username"], glucose)
                # print('sms simulation to: {0} {1} {2}'.format(uscout["emerg_contact"], uscout["username"], glucose))
                for phone in uscout["extra_contacts"]:
                    # print('sms simulation to: {0} {1} {2}'.format(phone, uscout["username"], glucose))
                    sms_glucose_alert(phone, uscout["username"], glucose)
    return "Event Received"

# Twilio webhooks
@app.route('/webhooks/twilio-inbound-messages', methods=["POST", "GET"])
def incoming_sms():
    body = request.values.get('Body', '')

    return "Event Received"
    
# Schedule Logic


# thread global var
thread = None


class ApplicationKilledException(Exception):
    pass

# Signal handler


def signal_handler(signum, frame):
    raise ApplicationKilledException("Killing signal detected")


start_scouts = False


def refresh_scouts():
    global active_scouts
    global start_scouts
    # Import Scout models for thread
    import models
    from models import model, scouts, scout


try:
    nightscouts = scouts()
    active_scouts = nightscouts.get_all()
    print("Refresh Scouts Job")
    if start_scouts == False:
        start_scouts = True

except:
    print("Error when refresh scouts")


# This job is executed certain periods of time to get the last nightscout entry
# If the glucose is not between the range then make a call to the personal phone notifiying the level
# If the call is not answered then events url is going to serve a NCCO sending SMS to the emergency number
# And if applicable any extra contacts


def job():
    # Calling nemo global client variable
    global client
    global active_scouts
    global nightscout_failed_pings
    global nightscout_failed_update_wait_mark
    global start_scouts

    print("Alerts Job")
    if active_scouts != None:
        if start_scouts == False:
            refresh_scouts('Starting_Scouts')
        for active_scout in active_scouts:
            print(active_scout["nightscout_api"])
            try:
                entries = requests.get(active_scout["nightscout_api"]).json()
                glucose = entries[0]['sgv']
                # No failed connection, so initialise the failed pings to zero for the active user
                nightscout_failed_pings[active_scout["phone"]] = 0
                # Check if the last NIGHTSCOUT entry doesn't exceed the NIGHTSCOUT NOT_UPDATE SECONDS limit.
                # In other words, this code verifies if nightscout entries get updates
                current_isoformat_datetime = datetime.utcnow().isoformat()
                nightscout_datetime = entries[0]['dateString']
                # Little trick to make UTC isodate from nodejs moment library compatible with python isoformat
                nightscout_isoformat_datetime = nightscout_datetime.replace(
                    "Z", "+00:00")
                # Difference in seconds between current time and last nightscout entry
                time_difference = calendar.timegm(datetime.fromisoformat(current_isoformat_datetime).utctimetuple(
                )) - calendar.timegm(datetime.fromisoformat(nightscout_isoformat_datetime).utctimetuple())
                print(time_difference, " ", os.getenv(
                    "NIGHTSCOUT_NOT_UPDATE_SECONDS"))
                if time_difference > int(os.getenv("NIGHTSCOUT_NOT_UPDATE_SECONDS")):
                    raise Exception("entry_update")
                else:
                    nightscout_failed_update_wait_mark[active_scout["phone"]] = 0

                # We add a dynamic attribute called glucose to pass glucose info to events url
                if 70 <= glucose <= 240:
                    print("{0} is inside the range for {1}".format(
                        glucose, active_scout["username"]))
                else:
                    print("Executing emergency call and loading sms NCCO if needed")
                    call_glucose_alert(active_scout["phone"], glucose)
            except KeyError:
                print("Key error")
            except Exception as instance:
                if instance.args[0] == 'entry_update':
                    handle_nightscout_failed_update(
                        active_scout["phone"], active_scout["nightscout_api"], active_scout["username"])
                    print(
                        "No updated entries for user, executing the failed update handler for user " + active_scout["username"])
                else:
                    handle_nightscout_failed_pings(
                        active_scout["phone"], active_scout["nightscout_api"], active_scout["username"])
                    print("Server could not establish connection with " +
                          active_scout["nightscout_api"])

def on_shutdown():
    print("Signal Detected: Killing Nightscout-Nexmo App.")
    scheduler.shutdown()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
scheduler = BackgroundScheduler() 
scheduler.add_job(func=job, trigger='cron', second=30)
scheduler.add_job(func=refresh_scouts, trigger='cron', hour='*')
scheduler.start()
print("Nightscout-Nexmo Thread starts")

atexit.register(on_shutdown)

call_glucose_alert('14049561232', 50)
