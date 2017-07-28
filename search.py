import pandas as pd
from sklearn.neighbors import NearestNeighbors
from typing import Tuple
from datetime import datetime, timedelta
import os


class AirRouteSearcher:

    def __init__(self, near_airports_count=5):

        self.airports_count = near_airports_count

        self.airports = pd.read_csv('airports.csv')
        self.airports = self.airports[['ident', 'name', 'type', 'latitude_deg', 'longitude_deg', 'municipality', 'iata_code']]
        self.airports = self.airports[self.airports.iata_code.notnull()]

        self.__flight_data_dir = 'flight_data'
        if not os.path.exists(self.__flight_data_dir):
            os.makedirs(self.__flight_data_dir)
        self.flight_data = []
        for filename in os.listdir(self.__flight_data_dir):
            self.flight_data.append(self.__load_data(os.path.join(self.__flight_data_dir, filename)))
        if len(self.flight_data):
            self.flight_data = pd.concat(self.flight_data)
        else:
            self.flight_data = pd.DataFrame({'dep_date': [], 'arr_date': [], 'Origin': [], 'Dest': []})
        self.neighbors = NearestNeighbors().fit(self.airports[['latitude_deg', 'longitude_deg']])

    def __load_data(self, path):
        data = pd.read_csv(path)
        data['hour'] = data['CRSDepTime'] // 100
        data['minute'] = data['CRSDepTime'] % 100
        data['day'] = data['DayofMonth']
        data['dep_date'] = pd.to_datetime(data[['Year', 'Month', 'day', 'hour', 'minute']])
        data['hour'] = data['CRSArrTime'] // 100
        data['minute'] = data['CRSArrTime'] % 100
        data['arr_date'] = pd.to_datetime(data[['Year', 'Month', 'day', 'hour', 'minute']])
        data = data[['dep_date', 'arr_date', 'Origin', 'Dest']]
        data.loc[data.arr_date < data.dep_date, 'arr_date'] += pd.DateOffset(days=1)
        return data

    def add_flight_data(self, data):
        path = os.path.join(self.__flight_data_dir, data.filename)
        data.save(path)
        self.flight_data = pd.concat((self.flight_data, self.__load_data(path)))

    def get_near_airports(self, coord: Tuple[float, float]):
        airports_distances, airports_indeces = self.neighbors.kneighbors([coord], n_neighbors=self.airports_count)
        return self.airports.iloc[airports_indeces[0]]

    def search_route(self, coord_from: Tuple[float, float], coord_to: Tuple[float, float], date: datetime) -> dict:
        near_airports_from = self.get_near_airports(coord_from)
        near_airports_to = self.get_near_airports(coord_to)

        comming_flightes = self.flight_data[(self.flight_data.dep_date - date <= pd.Timedelta(days=2))
                                            & (self.flight_data.dep_date - date >= pd.Timedelta(minutes=0))]

        all_flights = pd.DataFrame()

        last_flights = comming_flightes[comming_flightes.Origin.isin(near_airports_from.iata_code)
                                        & (comming_flightes.dep_date - date <= pd.Timedelta(days=1))
                                        & (comming_flightes.dep_date - date >= pd.Timedelta(minutes=0))]
        last_flights['previous'] = None

        while last_flights.shape[0] and not last_flights.Dest.isin(near_airports_to.iata_code).any():
            new_flights = []
            for flight in range(last_flights.shape[0]):
                flights = comming_flightes[(comming_flightes.Origin == last_flights.iloc[flight].Dest)
                            & (comming_flightes.dep_date - last_flights.iloc[flight].arr_date <= pd.Timedelta(days=1))
                            & (comming_flightes.dep_date - last_flights.iloc[flight].arr_date >= pd.Timedelta(hours=1))]
                flights['previous'] = all_flights.shape[0] + flight
                new_flights.append(flights)

            all_flights = pd.concat((all_flights, last_flights))
            last_flights = pd.concat(new_flights)

        if last_flights.shape[0] == 0:
            return {'route': 'Not found'}

        min_route = None
        min_wait = timedelta(days=10)
        for index, flight in last_flights[last_flights.Dest.isin(near_airports_to.iata_code)].iterrows():
            route = [flight]
            wait = timedelta(days=0)
            while flight.previous:
                wait += flight.dep_date - all_flights.iloc[flight.previous].arr_date
                flight = all_flights.iloc[flight.previous]
                route.append(flight)
            if wait < min_wait:
                min_wait = wait
                min_route = route

        route = []
        for flight in reversed(min_route):
            departure_airport = self.airports[self.airports.iata_code == flight.Origin].iloc[0]
            arrive_airport = self.airports[self.airports.iata_code == flight.Dest].iloc[0]
            route.append({
                'departure_date': flight.dep_date.strftime('%Y-%m-%d %H:%M'),
                'departure_iata_code': flight.Origin,
                'departure_airport': departure_airport['name'],
                'departure_latitude': departure_airport.latitude_deg,
                'departure_longitude': departure_airport.longitude_deg,
                'arrive_date': flight.arr_date.strftime('%Y-%m-%d %H:%M'),
                'arrive_iata_code': flight.Dest,
                'arrive_airport': arrive_airport['name'],
                'arrive_latitude': arrive_airport.latitude_deg,
                'arrive_longitude': arrive_airport.longitude_deg
            })

        return {'route': route}
