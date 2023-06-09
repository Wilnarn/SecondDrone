import math
import requests
import argparse
from sense_hat import SenseHat
import pygame
import redis
import pickle
import time
import threading
import json
sense = SenseHat()
pygame.mixer.init()
sense.clear()

redis_server = redis.Redis(host="192.168.3.4", port="7777", decode_responses=True, charset="unicode_escape")

def translate(coords_osm):
    x_osm_lim = (13.143390664, 13.257501336)
    y_osm_lim = (55.678138854000004, 55.734680845999996)

    x_svg_lim = (212.155699, 968.644301)
    y_svg_lim = (103.68, 768.96)

    x_osm = coords_osm[0]
    y_osm = coords_osm[1]

    x_ratio = (x_svg_lim[1] - x_svg_lim[0]) / (x_osm_lim[1] - x_osm_lim[0])
    y_ratio = (y_svg_lim[1] - y_svg_lim[0]) / (y_osm_lim[1] - y_osm_lim[0])
    x_svg = x_ratio * (x_osm - x_osm_lim[0]) + x_svg_lim[0]
    y_svg = y_ratio * (y_osm_lim[1] - y_osm) + y_svg_lim[0]

    return x_svg, y_svg

def redMatrix():
    #sense.clear()
    g = (0, 255, 0) # Green
    b = (0, 0, 0) # Black
    
    creeper_pixels = [
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, b, b, g, g, b, b, g,
        g, b, b, g, g, b, b, g,
        g, g, g, b, b, g, g, g,
        g, g, b, b, b, b, g, g,
        g, g, b, b, b, b, g, g,
        g, g, b, g, g, b, g, g
    ]
    
    sense.set_pixels(creeper_pixels)
    
def greenMatrix():
    #sense.clear()
    g = (0, 255, 0) # Green
    
    green_pixels = [
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g,
        g, g, g, g, g, g, g, g
    ]
    
    sense.set_pixels(green_pixels)
    
def yellowMatrix():
    #sense.clear()
    br = (168, 80, 50)
    bl = (0, 133, 168)
    s = (181, 127, 100)
    w = (255, 255, 255)
    
    steve_pixels = [
        br, br, br, br, br, br, br, br,
        br, br, br, br, br, br, br, br,
        br, s, s, s, s, s, s, br,
        
        s, s, s, s, s, s, s, s,
        s, w, bl, s, s, bl, w, s,
        s, s, s, br, br, s, s, s,
        s, s, br, s, s, br, s, s,
        s, s, br, br, br, br, s, s,
    ]
    
    sense.set_pixels(steve_pixels)

def check_job_queue(current_coords):
    while True:
        if redis_server.hget("Drone_1", 'status') == "idle" and redis_server.llen('drone_job_queue') > 0:
            serialized_job = redis_server.rpop('drone_job_queue')
            if serialized_job is not None:
                job_data = json.loads(serialized_job)
                newFrom = job_data['from']
                newTo = job_data['to']
                current_coords = run('Drone_1', current_coords, newFrom, newTo, SERVER_URL)
        time.sleep(1)
    
    
def waitForConf():
    joyTouched = True    
    pygame.mixer.music.load("doorbell.mp3")
    pygame.mixer.music.play()
    while joyTouched:
        yellowMatrix()
        for event in sense.stick.get_events():
            if event.action == "pressed":
                if event.direction == "middle":
                    pygame.mixer.music.load("coin.wav")
                    pygame.mixer.music.play()
                    joyTouched = False


def getMovement(src, dst):
    speed = 0.00001
    dst_x, dst_y = dst
    x, y = src
    direction = math.sqrt((dst_x - x)**2 + (dst_y - y)**2)
    longitude_move = speed * ((dst_x - x) / direction )
    latitude_move = speed * ((dst_y - y) / direction )
    return longitude_move, latitude_move
    
def getDirection(src, dst):
    dst_x, dst_y = dst
    x, y = src
    direction = math.sqrt((dst_x - x)**2 + (dst_y - y)**2)
    return direction
    
def getChargerStation(src):
    c1 = (13.19974, 55.70382)
    c2 = (13.20727, 55.72358)
    c3 = (13.19953, 55.69552)
    d1 = getDirection(src, c1)
    d2 = getDirection(src, c2)
    d3 = getDirection(src, c3)
    closest = min(d1, d2, d3)
    if (closest == d1):
        return c1
    elif (closest == d2):
        return c2
    else:
        return c3

def moveDrone(src, d_long, d_la):
    x, y = src
    x = x + d_long
    y = y + d_la        
    return (x, y)
    
def run(id, current_coords, from_coords, to_coords, SERVER_URL):
    waitForConf()
    drone_coords = current_coords
    d_long, d_la =  getMovement(drone_coords, from_coords)
    #flyger till upphämtning
    while ((from_coords[0] - drone_coords[0])**2 + (from_coords[1] - drone_coords[1])**2)*10**6 > 0.0002:
        redMatrix()
        drone_coords = moveDrone(drone_coords, d_long, d_la)
        with requests.Session() as session:
            drone_info = {'id': id,
                          'longitude': drone_coords[0],
                          'latitude': drone_coords[1],
                          'status': 'busy'
                        }
            resp = session.post(SERVER_URL, json=drone_info)
    d_long, d_la =  getMovement(drone_coords, to_coords)
    waitForConf()
    #flyger till avlämning
    while ((to_coords[0] - drone_coords[0])**2 + (to_coords[1] - drone_coords[1])**2)*10**6 > 0.0002:
        redMatrix()
        drone_coords = moveDrone(drone_coords, d_long, d_la)
        with requests.Session() as session:
            drone_info = {'id': id,
                          'longitude': drone_coords[0],
                          'latitude': drone_coords[1],
                          'status': 'busy'
                        }
            resp = session.post(SERVER_URL, json=drone_info)
    waitForConf()
    
   # while redis_server.llen('drone_job_queue') > 0:
    #    serialized_job = redis_server.rpop('drone_job_queue')
     #   job_data = json.loads(serialized_job)
      #  newFrom = job_data['from']
       # newTo = job_data['to']
        #drone_coords = run(id, drone_coords, newFrom, newTo, SERVER_URL)
    d_long, d_la =  getMovement(drone_coords, charge_coords)
    #flyger till laddstation (charge_coords här)
    while ((charge_coords[0] - drone_coords[0])**2 + (charge_coords[1] - drone_coords[1])**2)*10**6 > 0.0002:
        redMatrix()
        drone_coords = moveDrone(drone_coords, d_long, d_la)
        with requests.Session() as session:
            drone_info = {'id': id,
                          'longitude': drone_coords[0],
                          'latitude': drone_coords[1],
                          'status': 'busy'
                        }
            resp = session.post(SERVER_URL, json=drone_info)
    greenMatrix()
    waitForConf()
    with requests.Session() as session:
            drone_info = {'id': id,
                          'longitude': drone_coords[0],
                          'latitude': drone_coords[1],
                          'status': 'idle'
                         }
            resp = session.post(SERVER_URL, json=drone_info)
    waitForConf()
    check_job_queue(charge_coords)
    #return drone_coords[0], drone_coords[1]
    greenMatrix()
    return drone_coords
   
if __name__ == "__main__":
    
    threading.Thread(target=check_job_queue, daemon=True).start()
    # Fill in the IP address of server, in order to location of the drone to the SERVER
    #===================================================================
    SERVER_URL = "http://192.168.3.4:5001/drone"
    #===================================================================

    parser = argparse.ArgumentParser()
    parser.add_argument("--clong", help='current longitude of drone location' ,type=float)
    parser.add_argument("--clat", help='current latitude of drone location',type=float)
    parser.add_argument("--flong", help='longitude of input [from address]',type=float)
    parser.add_argument("--flat", help='latitude of input [from address]' ,type=float)
    parser.add_argument("--tlong", help ='longitude of input [to address]' ,type=float)
    parser.add_argument("--tlat", help ='latitude of input [to address]' ,type=float)
    parser.add_argument("--id", help ='drones ID' ,type=str)
    args = parser.parse_args()

    current_coords = (args.clong, args.clat)
    from_coords = (args.flong, args.flat)
    to_coords = (args.tlong, args.tlat)
    charge_coords = getChargerStation(to_coords)

    print(current_coords, from_coords, to_coords)
    drone_long, drone_lat = run(args.id ,current_coords, from_coords, to_coords, SERVER_URL)
    file = open('dcoords.txt', 'w')
    file.write(str(drone_long) + "\n" + str(drone_lat))
    # drone_long and drone_lat is the final location when drlivery is completed, find a way save the value, and use it for the initial coordinates of next delivery
    #=============================================================================
