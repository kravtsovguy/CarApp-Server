print('start server...');

from flask import Flask
from flask import jsonify
from flask import request
import os
import pyrebase
from scipy.stats import norm
import json
import database_api

config = {
	"apiKey": "AIzaSyACDOJqP1_-6jYKCmk8LJ-svl5_Lpk9PWw",
	"databaseURL": "https://carapp-9f21c.firebaseio.com",
	"authDomain": "carapp-9f21c.firebaseapp.com",
	"storageBucket": "carapp-9f21c.appspot.com"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()
'''
auth = firebase.auth()

user = auth.sign_in_with_email_and_password("kravtsovguy@gmail.com", "carapp")

def refresh_token():
	user = auth.refresh(user['refreshToken'])

def get_token():
	return user['idToken']
'''

def recalc_consumption(car_id):
	consumptions = db.child("cars").child(car_id).child("measurements").get()
	m_consumption = 0.0
	d_consumption = 0.0
	count = db.child("cars").child(car_id).child("measurements_count").get().val()
	if count == None or count == 0:
		return None

	for c in consumptions.each():
		m_consumption += c.val()

	m_consumption = m_consumption / count

	for c in consumptions.each():
		d_consumption += (c.val() - m_consumption) ** 2

	if count == 1:
		d_consumption = 0
	else:
		d_consumption = (d_consumption / (count - 1)) ** 0.5

	prior_index = db.child("cars").child(car_id).child("prior_index").get().val()
	if prior_index != None:
		prior_koeff = (1 / (0.1 * count + 1)) ** 0.5
		#print('prior_koeff: ' + str(prior_koeff))
		m_consumption = prior_koeff * prior_index['m_consumption'] + (1 - prior_koeff) * m_consumption
		d_consumption = prior_koeff * prior_index['d_consumption'] + (1 - prior_koeff) * d_consumption

	consumption = {"m_consumption":m_consumption, "d_consumption":d_consumption}
	db.child("cars").child(car_id).child("index").update(consumption)

	return consumption

def get_status_consumption(car_id, consumption):
	index = db.child("cars").child(car_id).child("index").get().val()
	m = (consumption - index["m_consumption"]) / index["d_consumption"]
	p = 1 - norm.cdf(m)

	type1_error_warning = 5.0 / 100
	type1_error_alert = 1.0 / 100

	status = 'OK'
	if (p < type1_error_warning):
		status = 'warning'
	if (p < type1_error_alert):
		status = 'alert'

	return {'p_level' : p, 'car_status': status}

app = Flask(__name__)

@app.route("/")
def hello():
    return jsonify("This is CarApp server!")

@app.route("/car",  methods=['GET'])
def get_car_marks():
	cars = db.child("cars").shallow().get().val()
	list_cars = list(cars)
	return jsonify({"marks":list_cars})

@app.route("/car/<car_mark>",  methods=['GET'])
def get_car_models(car_mark):
	cars = db.child("cars").child(car_mark).shallow().get().val()
	list_cars = list(cars)
	return jsonify({"models":list_cars})

@app.route("/car/<car_mark>/<car_model>",  methods=['GET'])
def get_car(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	car = db.child("cars").child(car_id).child("info").get().val()
	return jsonify(car)

@app.route("/car/<car_mark>/<car_model>",  methods=['POST'])
def set_car(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	data = request.get_json()

	description = data["description"]
	if description != 0:
		db.child("cars").child(car_id).child("info").update({"description" : description})

	image_url = data["image"]
	if image_url != 0:
		db.child("cars").child(car_id).child("info").update({"image" : image_url})

	return jsonify({"status":"OK"})

@app.route("/car/index/<car_mark>/<car_model>",  methods=['GET'])
def get_index_car(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	index = db.child("cars").child(car_id).child("index").get().val()
	if index == None:
		index = db.child("cars").child(car_id).child("prior_index").get().val()

	return jsonify(index)

@app.route("/car/prior_index/<car_mark>/<car_model>",  methods=['GET'])
def get_prior_index_car(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	index = db.child("cars").child(car_id).child("prior_index").get().val()
	return jsonify(index)

@app.route("/car/prior_index/<car_mark>/<car_model>",  methods=['POST'])
def set_prior_index_car(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	data = request.get_json()
	consumption = data["consumption"]
	db.child("cars").child(car_id).child("prior_index").update({"m_consumption":consumption, "d_consumption":2})
	return jsonify({"status":"OK"})

@app.route("/car/index/<car_mark>/<car_model>",  methods=['POST'])
def update_index_car(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	data = request.get_json()
	consumption = data["consumption"]

	index = db.child("cars").child(car_id).child("index").get().val()
	if index == None:
		index = db.child("cars").child(car_id).child("prior_index").get().val()

	m = index["m_consumption"]
	d = index["d_consumption"]
	if consumption < (m - 3 * d) or (m + 3 * d) < consumption:
		return jsonify(None)


	mc = db.child("cars").child(car_id).child("measurements_count").get().val()
	if mc == None:
		mc = 0

	db.child("cars").child(car_id).child("measurements").child(mc).set(consumption)
	db.child("cars").child(car_id).child("measurements_count").set(mc+ 1)

	result = recalc_consumption(car_id)
	return jsonify(result)

@app.route("/car/status/<car_mark>/<car_model>",  methods=['POST'])
def get_status(car_mark, car_model):
	car_id = car_mark + '/' + car_model
	data = request.get_json()
	consumption = data["consumption"]
	result = get_status_consumption(car_id, consumption)
	return jsonify(result)

@app.route('/login', methods=['POST'])
def page_sign_in():
	#data = json.loads(request.data)
	data = request.get_json()
	email = data['email']
	password = data['password']

	print(email+" "+password)

	result = database_api.sign_in(email, password)
	return jsonify(result)

@app.route('/signup', methods=['POST'])
def page_sign_up():
	#data = json.loads(request.data)
	data = request.get_json()
	email = data['email']
	password = data['password']
	name = data['name']

	result = database_api.sign_up(email, password)
	return jsonify(result)

def set_user_info_main(token, info):
	result = database_api.set_user_info(token, info)
	return jsonify(result)

@app.route('/user', methods=['POST'])
def set_user_info():
	data = request.get_json()
	#data = json.loads(request.data)
	token = request.args['token']
	print(data["info"])
	#info = json.loads('{"name" : "Mike"}')
	#info = json.loads(data['info'])
	info = data['info']
	return set_user_info_main(token, info)

@app.route('/user', methods=['GET'])
def get_user_info():
	#data = json.loads(request.data)
	token = request.args['token']
	result = database_api.get_user_info(token)
	return jsonify(result)


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host='0.0.0.0', port=port)
