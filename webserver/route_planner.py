from cmath import pi
from flask import Flask, request, render_template, jsonify
from flask.globals import current_app 
from geopy.geocoders import Nominatim
from flask_cors import CORS
import redis
import json
import requests

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'dljsaklqk24e21cjn!Ew@@dsa5'

redis_server = redis.Redis(host="localhost", port="7777", decode_responses=True, charset="unicode_escape")

geolocator = Nominatim(user_agent="my_request")
region = ", Lund, Skåne, Sweden"

def send_request(drone_url, coords):
    with requests.Session() as session:
        resp = session.post(drone_url, json=coords)

@app.route('/planner', methods=['POST'])
def route_planner():
    Addresses =  json.loads(request.data.decode())
    FromAddress = Addresses['faddr']
    ToAddress = Addresses['taddr']
    from_location = geolocator.geocode(FromAddress + region, timeout=None)
    to_location = geolocator.geocode(ToAddress + region, timeout=None)
    if from_location is None:
        message = 'Departure address not found, please input a correct address'
        return message
    elif to_location is None:
        message = 'Destination address not found, please input a correct address'
        return message
    else:
        coords = {'from': (from_location.longitude, from_location.latitude),
                  'to': (to_location.longitude, to_location.latitude),
                  }
        drone1 = redis_server.hget("Drone_1", 'status')

        if (drone1 == "idle"):
            DRONE_URL = 'http://' + redis_server.hget("Drone_1", 'IP')+':5000'
            message = 'Got address and sent request to the drone'
            send_request(DRONE_URL, coords)
        
        elif (drone1 == 'busy'):
            message = 'Drone is currently busy, your delivery will be handled when it is done'
            job = {
                'from': (from_location.longitude, from_location.latitude),
                'to': (to_location.longitude, to_location.latitude)
            }
            redis_server.lpush('drone_job_queue', json.dumps(job))
        else:
            message = 'ERROR'
        
        return message
    return message

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port='5002')

