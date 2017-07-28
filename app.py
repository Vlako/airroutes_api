from flask import Flask, request
from search import AirRouteSearcher
from datetime import datetime
import json
import googlemaps
from config import googlemaps_key

app = Flask(__name__)
gmaps = googlemaps.Client(key=googlemaps_key)
searcher = AirRouteSearcher()


@app.route('/route', methods=['GET'])
def route():
    latitude_from = request.args.get('latitude_from', type=float)
    longitude_from = request.args.get('longitude_from', type=float)
    latitude_to = request.args.get('latitude_to', type=float)
    longitude_to = request.args.get('longitude_to', type=float)

    address_from = request.args.get('address_from')
    if address_from:
        address_from = gmaps.geocode(address_from)
        latitude_from = address_from[0]['geometry']['location']['lat']
        longitude_from = address_from[0]['geometry']['location']['lng']
    address_to = request.args.get('address_to')
    if address_to:
        address_to = gmaps.geocode(address_to)
        latitude_to = address_to[0]['geometry']['location']['lat']
        longitude_to = address_to[0]['geometry']['location']['lng']

    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    day = request.args.get('day', type=int)
    hour = request.args.get('hour', 0, type=int)
    minute = request.args.get('minute', 0, type=int)
    if any([latitude_from is None, longitude_from is None, latitude_to is None, longitude_to is None]):
        return json.dumps({'error': 'Parameters are required for the origin and destination points:' +
                                    'latitude_from and longitude_from or address_from; latitude_to and longitude_to or address_to'})
    if any([year is None, month is None, day is None]):
        return json.dumps({'error': 'Parameters are required for the date of departure: year, month, day'})
    date = datetime(year, month, day, hour, minute)

    route = searcher.search_route((latitude_from, longitude_from), (latitude_to, longitude_to), date)
    return json.dumps(route)


@app.route('/flight_data', methods=['POST'])
def flight_data():
    file = request.files['file']
    searcher.add_flight_data(file)
    return json.dumps({'result': 'OK'})

if __name__ == '__main__':
    app.run()
