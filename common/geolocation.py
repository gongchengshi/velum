import requests


class GeolocationException(Exception):
    def __init__(self, reason=None):
        super(GeolocationException, self).__init__(reason)


class Geolocation:
    def __init__(self, city, region, country, lat, lon):
        self.city = city
        self.region = region
        self.country = country
        self.lat = lat
        self.lon = lon


def get_geolocation(ip_address):
    # Todo: First try using MaxMind's free and downloadable GeoLite2 database.
    # If that fails then fail over to a remote service.
    try:
        response = requests.get('http://www.freegeoip.net/json/%s' % ip_address, timeout=3)
        response.raise_for_status()
        j = response.json()
        geolocation = Geolocation(j['city'], j['region_name'], j['country_name'],
                                  float(j['latitude']), float(j['longitude']))
    except:
        try:
            response = requests.get('http://ip-api.com/json/%s' % ip_address, timeout=3)
            response.raise_for_status()
            j = response.json()
            if j['status'] != 'success':
                raise Exception()
            geolocation = Geolocation(j['city'], j['regionName'], j['country'],
                                      float(j['lat']), float(j['lon']))
        except:
            raise GeolocationException("Could not retrieve geolocation information.")
    return geolocation


from python_common.geocoding.geopyplus import GeoPyPlus

geocoder = GeoPyPlus()


def get_lat_long(ip_address):
    geolocation = get_geolocation(ip_address)
    if geolocation.lat and geolocation.lon:
        return geolocation.lat, geolocation.lon
    else:
        try:
            location_info = geocoder.geocode(', '.join([geolocation.city, geolocation.region, geolocation.country]))
            return location_info.latitude, location_info.longitude
        except:
            return None, None
