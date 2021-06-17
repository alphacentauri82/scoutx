
# Load Firebase configuration
from firebase_admin import firestore
import firebase_admin
import os, json
from firebase_admin import credentials
from os.path import join, dirname
from dotenv import load_dotenv

# get the private key from environment
envpath = join(dirname(__file__), "./.env")
load_dotenv(envpath)

firebase_private_key = os.getenv("FIREBASE_PRIVATE_KEY")

#Verify if private key is not a file
if not os.path.isfile(firebase_private_key):
    #Convert json string into dict
    firebase_private_key = json.loads(firebase_private_key)

# get the credentials
credits = credentials.Certificate(firebase_private_key)
# Init the application
firebase_admin.initialize_app(credits)
# use databaseUrl parameter when using real time database
# "databaseURL": "https://whatevername.firebaseio.com"

# Create a persistance reference for all App
#from firebase_admin import db


class model:
    def __init__(self, key):
        self.key = key
        self.db = firestore.client()
        self.collection = self.db.collection(self.key)

    def get_by(self, field, value):
        docs = list(self.collection.where(
            field, u'==', u'{0}'.format(value)).stream())
        item = None
        if docs != None:
            if len(docs) > 0:
                item = docs[0].to_dict()
                item['id'] = docs[0].id
        return item

    def get_all(self):
        docs = self.collection.stream()
        items = []
        for doc in docs:
            item = None
            item = doc.to_dict()
            item['id'] = doc.id
            items.append(item)
        if len(items) > 0:
            return items
        else:
            return None

    def add(self, data, id=None):
        if id == None:
            self.collection.add(data)
        else:
            self.collection.document(u'{0}'.format(id)).set(data)
        return True

    def update(self, data, id):
        if id != None:
            if data != None:
                doc = self.collection.document(u'{id}'.format(id=id))
                doc.update(data)
        return False


class scout:
    def __init__(self, email='', username='', nightscout_api='', phone='', emerg_contact='', extra_contacts=[]):
        self.email = email
        self.username = username
        self.nightscout_api = nightscout_api
        self.phone = phone
        self.emerg_contact = emerg_contact
        self.extra_contacts = extra_contacts


class scouts(model):
    def __init__(self):
        super().__init__(u'scouts')

    def get_by_email(self, email):
        docs = list(self.collection.where(
            u'email', u'==', u'{0}'.format(email)).stream())
        item = None
        if docs != None:
            if len(docs) > 0:
                item = docs[0].to_dict()
                item['id'] = docs[0].id
        return item

    def getby_personal_phone(self, phone):
        return self.get_by(u'phone', phone)

    def add(self, data, id=None):
        if type(data) is scout:
            super().add(data.__dict__, id)
        else:
            super().add(data, id)
