import configparser
import requests
#import urllib2
import json
import time
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests.exceptions import ConnectionError
from Adafruit_IO import Client

config = configparser.ConfigParser()
config.read('config.ini')

delay = float(config['GENERAL']['Delay'])
output = config['GENERAL'].get('Output', fallback=True)

influxAddress = config['INFLUXDB']['Address']
influxPort = config['INFLUXDB']['Port']
influxDatabase = config['INFLUXDB']['Database']
influxUser = config['INFLUXDB'].get('Username', fallback='')
influxPassword = config['INFLUXDB'].get('Password', fallback='')

adafruitapikey = config['ADAFRUIT']['APIKey']
#Feeds = config['ADAFRUIT']['Feeds']
Feeds = json.loads(config['ADAFRUIT'].get('Feeds'))

aio = Client(adafruitapikey)

influx_client = InfluxDBClient(influxAddress, influxPort, influxUser, influxPassword, influxDatabase)

def getAdafruitData():

    data_list = []

    listFeeds = aio.feeds()

    for iofeed in listFeeds:
        for inifeed in Feeds:
            if inifeed == iofeed.key:
                data = aio.receive(inifeed)
                data_list.append(formatData(data, inifeed))

    return data_list

def formatData(data, inifeed):

    json_body = [
        {
            "measurement": "adafruit",
            "tags": {
                "feed": inifeed
            },
            "time": data.created_at,
            "fields": {
                "value": data.value
            }
        }
    ]

    return json_body

def sendInfluxData(json_data):

    #if output:
        #print(json_data)
        #print(type(json_data))

    try:
        influx_client.write_points(json_data)
    except (InfluxDBClientError, ConnectionError, InfluxDBServerError) as e:
        if hasattr(e, 'code') and e.code == 404:

            print('Database {} Does Not Exist.  Attempting To Create'.format(influxDatabase))

            influx_client.create_database(influxDatabase)
            influx_client.write_points(json_data)

            return

        print('ERROR: Failed To Write To InfluxDB')
        print(e)

    if output:
        print('Written To Influx: {}'.format(json_data))


def main():
    while True:
        adafruitData = getAdafruitData()

        for feed in adafruitData:

            sendInfluxData(feed)

        time.sleep(delay)

if __name__ == '__main__':
    main()
