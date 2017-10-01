import os
import requests
import pyre
from requests.exceptions import HTTPError

config = {
	"apiKey": "AIzaSyACDOJqP1_-6jYKCmk8LJ-svl5_Lpk9PWw",
	"databaseURL": "https://carapp-9f21c.firebaseio.com",
	"authDomain": "carapp-9f21c.firebaseapp.com",
	"storageBucket": "carapp-9f21c.appspot.com",
	"projectId": "carapp-9f21c",
}

firebase = pyre.initialize_app(config)
auth = firebase.auth()
db = firebase.database()
storage = firebase.storage()

UPLOAD_FOLDER = 'images/'

def sign_in(email, password):
	temp = auth.sign_in_with_email_and_password(email, password)
	#print(temp)
	return temp
	#data = {"name": "ya admin bleat"}
	#db.child("users").child(user['localId']).set(data, user['idToken'])

def sign_up(email, password):
	temp = auth.create_user_with_email_and_password(email, password)
	#print(temp)
	return temp

def get_uid(idToken):
	res = auth.get_account_info(idToken)
	print(res)
	if not 'users' in res:
		return None
	if len(res['users']) < 1:
		return None
	return res['users'][0]['localId']

def get_user_info(idToken):
	uid = get_uid(idToken)
	if uid == None:
		return { 'error' : 'Invalid token' }

	res = db.child("users").get(idToken)
	if uid in res.val():
		user = db.child("users").child(uid).child("info").get(idToken)
		return { 'userId': uid, 'info': user.val() }

	return { 'error' : 'Server internal failure'}

def set_user_info(idToken, info):
	uid = get_uid(idToken)
	print(uid)
	if uid == None:
		return { 'error' : 'Invalid token' }

	db.child("users").child(uid).child("info").update(info, idToken)
	user = db.child("users").child(uid).child("info").get(idToken)

	return { 'userId': uid, 'info': user.val() }