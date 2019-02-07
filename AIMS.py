from flask import Flask, jsonify,request, make_response
import requests
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
import random
from functools import wraps
import jwt
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'SDEFinalProject'

#db is  object that allow to interact ot our database
db =SQLAlchemy(app)

########################################################################################################################
''' Our database contain three tables

    User table - It is used to manage users.
    Field table - It is used to manage farm field.
    Crop table - It is used to store crop detail information.
   '''


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(50))
    admin = db.Column(db.Boolean)


class Field(db.Model):
    field_id = db.Column(db.Integer, primary_key=True)
    region_name = db.Column(db.String(100))
    village_name = db.Column(db.String(100))
    farmer_name = db.Column(db.String(100))


class Crop(db.Model):
    crop_id = db.Column(db.Integer, primary_key=True)
    crop_name = db.Column(db.String(100))
    crop_description = db.Column(db.String(2000))


#######################################################################################################################
#This is a login endpoint

@app.route('/login')
def login():
    auth = request.authorization

     #check wheather the user not enter username or password or both
    if not auth or not auth.username or not auth.password:
        return make_response('Please check your login information!', 401, {'WWW-Authenticate' : 'Basic realm="It required login!"'})

    user = User.query.filter_by(username=auth.username).first()

    if not user:
        return make_response('Not authorized user, please check your login information', 401, {'WWW-Authenticate' : 'Basic realm="It required login!"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'user_id':'user.user_id', 'exp':datetime.datetime.utcnow() + datetime.timedelta(minutes=300)}, app.config['SECRET_KEY'])

        return jsonify({'token':token.decode('UTF-8')}), 200

    return make_response('you entered wrong password!', 401, {'WWW-Authenticate' : 'Basic realm="It required login!"'})


#######################################################################################################################

#Most endpoints in our service it requires a token.
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'token' in request.headers:
            token = request.headers['token']

        if not token:
            return jsonify({'error':'Missing Token'}), 401

        try:
            get_data = jwt.decode(token, app.config['SECRET_KEY'])
            user = User.query.filter_by(user_id=get_data['user_id']).first()
        except:
            return jsonify({'error':'Invalid Token'}), 401

        return f(user, *args, **kwargs)

    return decorated
#######################################################################################################################
# This is a User Management Service. It contian following endpoints.

@app.route('/register', methods=['POST']) #This endpoint allows to register user.
def register_user():

    data = request.get_json()

    hashed_password = generate_password_hash(data['password'], method='sha256')

    new_user = User(user_id=random.randint(1000, 9999), username=data['username'], password=hashed_password, admin=False)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'Message': 'The new user successfully created!'}), 201


@app.route('/users', methods=['GET']) # This endpoint allows to access all users from the db.
def get_all_users():

    users = User.query.all()

    output = []

    for user in users:
        user_data = {}
        user_data['User_id'] = user.user_id
        user_data['Username'] = user.username
        user_data['Password'] = user.password
        user_data['Admin'] = user.admin

        output.append(user_data)

    return jsonify({'List of users': output}), 200


@app.route('/user/<user_id>', methods=['GET']) # This endpoint allows to access a single user from the db by a given user id.
def get_specific_user(user_id):

    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({'error': 'the requested user not found in the database!'}),404

    user_data = {}
    user_data['User_id'] = user.user_id
    user_data['Username'] = user.username
    user_data['Password'] = user.password
    user_data['Admin'] = user.admin

    return jsonify({'User': user_data}), 200


@app.route('/user/<user_id>', methods=['PUT']) # This endpoint allows to modify the existed user in the db by a given user id.
def update_specific_user(user_id):

    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({'error': 'the requested user not found in the database!'}), 404

    username = request.json['username']
    password = request.json['password']

    hashed_password = generate_password_hash(password, method='sha256')

    user.username = username
    user.password = hashed_password


    db.session.commit()

    return jsonify({'Message': 'The user successfully updated!'}), 202


@app.route('/user/<user_id>', methods=['DELETE']) # This endpoint allows to delete the user from the db.
def delete_specific_user(user_id):

    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({'error':'the requested user not found in the database!'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'message':'User deleted successfully!'}), 202

#######################################################################################################################
#This is Field Management Service. It contain the following endpoints.

@app.route('/fields', methods=['GET'])# This endpoint allows to access all created fields from the db.
@token_required
def get_all_field(user):
    fields = Field.query.all()

    output = []

    for field in fields:
        field_data = {}
        field_data['Field_id'] = field.field_id
        field_data['Region_name'] = field.region_name
        field_data['Village_name'] = field.village_name
        field_data['Farmer_name'] = field.farmer_name

        output.append(field_data)

    return jsonify({'List of fields': output}), 200


@app.route('/field/<field_id>', methods=['GET']) # This endpoint allows to access a single field from the db by a given field id.
@token_required
def get_single_field(user, field_id):
    field = Field.query.filter_by(field_id=field_id).first()

    if not field:
        return jsonify({'error': 'the requested field not found in the database!'}), 404

    field_data = {}
    field_data['Field_id'] = field.field_id
    field_data['Region_name'] = field.region_name
    field_data['Village_name'] = field.village_name
    field_data['Farmer_name'] = field.farmer_name

    return jsonify({'Field': field_data}), 200


@app.route('/field', methods=['POST']) # This endpoint allows to create a new field.
@token_required
def create_field(user):
    data = request.get_json()
    new_field = Field(field_id=random.randint(10000, 99999), region_name=data['region_name'],  village_name=data['village_name'],
                      farmer_name=data['farmer_name'])

    db.session.add(new_field)
    db.session.commit()

    return jsonify({'Message': 'New field created successfully!'}), 201


@app.route('/field/<field_id>', methods=['PUT']) # This endpoint allows update an existed field by a given field id.
@token_required
def update_field(user, field_id):
    field = Field.query.get(field_id)

    if not field:
        return jsonify({'error':'the requested field not found in the database!'}), 404

    region_name = request.json['region_name']
    village_name = request.json['village_name']
    farmer_name = request.json['farmer_name']

    field.region_name = region_name
    field.village_name = village_name
    field.farmer_name = farmer_name

    db.session.commit()

    return jsonify({'Message':'The field update successfully'}),202


@app.route('/field/<field_id>', methods=['DELETE']) # This endpoint allows to delete an existed field by given field id.
@token_required
def delete_field(user, field_id):
    field = Field.query.filter_by(field_id=field_id).first()

    if not field:
        return jsonify({'error':'the requested field not found in the database!'}), 404

    db.session.delete(field)
    db.session.commit()

    return jsonify({'Message':'Field deleted successfully!'}), 202

#######################################################################################################################
''' This is Crop Management Service. It contains different endpoints. Among the following endpoints we only expose the access part of the service to the users i.e get
  get_all_crop and get_one_crop endpoints.
  '''

@app.route('/crops', methods=['GET'])# This endpoint allows to access all crops information.
@token_required
def get_all_crop(user):

    crops = Crop.query.all()

    output = []

    for crop in crops:
        crop_data = {}
        crop_data['crop_id'] = crop.crop_id
        crop_data['crop_name'] = crop.crop_name
        crop_data['crop_description'] = crop.crop_description
        output.append(crop_data)

    return jsonify({'List of crops': output}), 200



@app.route('/crop/<crop_name>', methods=['GET']) # This endpoint allows to access a single crop informatin by providing a crop name.
@token_required
def get_one_crop(user, crop_name):
    crop = Crop.query.filter_by(crop_name=crop_name).first()

    if not crop:
        return jsonify({'Error': 'the requested crop name not found in the database!'}), 404


    crop_data = {}
    crop_data['crop_id'] = crop.crop_id
    crop_data['crop_name'] = crop.crop_name
    crop_data['crop_description'] = crop.crop_description


    return jsonify({'Crop': crop_data}), 200


@app.route('/crop', methods=['POST']) # This endpoint allows to create a crop information.
@token_required
def create_crop(user):
    data = request.get_json()
    new_crop = Crop(crop_id=random.randint(100, 999), crop_name=data['crop_name'], crop_description=data['crop_description'])

    db.session.add(new_crop)
    db.session.commit()

    return jsonify({'Message': 'New crop created successfully!'}), 201


@app.route('/crop/<crop_id>', methods=['PUT']) # This endpoint allows to modify the existing crop information by providing crop id.
@token_required
def update_crop(user, crop_id):
    crop = Crop.query.get(crop_id)

    if not crop:
        return jsonify({'error': 'the requested crop not found in the database!'}), 404

    crop_name = request.json['crop_name']
    crop_description = request.json['crop_description']

    crop.crop_name = crop_name
    crop.crop_description = crop_description


    db.session.commit()

    return jsonify({'Message': 'The crop update successfully'}), 202


@app.route('/crop/<crop_id>', methods=['DELETE']) # This endpoint allows to delete a crop information by providing crop id.
@token_required
def delete_crop(user, crop_id):
    crop = Crop.query.filter_by(crop_id=crop_id).first()

    if not crop:
        return jsonify({'error': 'the requested crop not found in the database!'}), 404

    db.session.delete(crop)
    db.session.commit()

    return jsonify({'Message': 'Crop deleted successfully!'}), 202


########################################################################################################################
# The following are different api keys that are used in our application  to access different external service.

geocoding_access_token = "pk.eyJ1Ijoic2V3dXJva2lrIiwiYSI6ImNqcTlxamM4eDBzdXk0N3FnZWx2azJ2M2oifQ.HVin0OOoCRG6aV8CPGIQhA"
weather_access_token = "a294661c76002dac5bd879b4b25c396d"
soil_info_key = "526c2a3ca25e421ba838d27b30c793e2"
commodity_api_key = "Em2X3qURsrqkCVmbh536"

########################################################################################################################

#First process centric process- Field information Service


@app.route('/field_info/<field_id>', methods=['GET'])
@token_required
def field_info(user, field_id):




    """" This endpoint used to generate the following information about the farm field by providing the field_id:
         -Current weather condition
         -5-days forecast weather condition
         -8-days Soil information

         In order to provide these informations, our service integrated with other external services.

         -Geocoding service(External Service)
            -we use these service provide the latitude and longitude of a specific location(the location of the field)

         - Weather information(External service)
            -we use this service to get weather infromation by a specific latitude and longitude of the location.

         -Soil information service (External service)
            - we use this service to get soil data by a specific latitude and longitude of the location.


         When the user enter the field_id of a specific field then our internal service take this id and
         verify it in the database. If the id is found in the database then it return the location of the field. If not it return error message.
    """
    try:

        field = Field.query.filter_by(field_id=field_id).first()

        if not field:
            return jsonify({'error': 'the requested field not found in the database!'}), 404

        field_data = {}

        field_data['Village_name'] = field.village_name
        location_name = field_data['Village_name']

        # now we get the location of name of the field
        loc_name = json.dumps(location_name)


#Now we calling Gecoding service(in our case we use mapbox service )to get the latitude and longitude of the location name.
#In the above we already got loc_name and then we pass this as parameter to get latitude and longitude of the location name.



    #This is the url we request the coordiante of a specific place
        Geocode_url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + loc_name + ".json"

    # mapbox_access_token and query are the parameters the include in the request
        Geocode_param = {'access_token': geocoding_access_token, 'query': loc_name}

    # Now we are requesting using url(Gecode_url) and parameters(Geocode_param)
        Geocode_request = requests.get(Geocode_url, params=Geocode_param)

    # Now we get a json data
        Geocode_json = Geocode_request.json()

    # but we are specifically intersted on geometry(lat and lon)
        lat_json = Geocode_json["features"][0]["geometry"]["coordinates"][1]
        lon_json = Geocode_json["features"][0]["geometry"]["coordinates"][0]

    # convert the dictionary to a string using json.dumps
        lat = json.dumps(lat_json)
        lon = json.dumps(lon_json)

# Then now we pass lat and lon to get weather information and soil data.

    #current weather condition

        current_weather_url = "https://api.openweathermap.org/data/2.5/weather?lat=" + lat + "&lon=" + lon
        current_weather_param = {'appid': weather_access_token, 'lat': lat, 'lon': lon, 'units': 'metric'}
        current_weather_request = requests.get(current_weather_url, params=current_weather_param)

        #Get current weather data in json format
        current_weather_json = current_weather_request.json()

    #  5-day forecast includes weather data every 3 hours

        forecast_weather_url = "https://api.openweathermap.org/data/2.5/forecast?lat=" + lat + "&lon=" + lon
        forecast_weather_param = {'appid': weather_access_token, 'lat': lat, 'lon': lon, 'units': 'metric'}
        forecast_weather_request = requests.get(forecast_weather_url, params=forecast_weather_param)

        #Get 5-day forecast weather data in json format
        forecast_weather_json = forecast_weather_request.json()


    # 8-day forecast soil temperature, soil moisture, evapotranspiration, and more by provide lat and lon.

        soil_info_url = "https://api.weatherbit.io/v2.0/forecast/agweather?lat=" + lat + "&lon=" + lon
        soil_info_param = {'key': soil_info_key, 'lat': lat, 'lon': lon}
        soil_info_request = requests.get(soil_info_url, params=soil_info_param)

        #Get 8-day forecast soil data in json format
        soil_info_json = soil_info_request.json()

    except:
             return jsonify({'Error':'Wrong field Id'})



    #finally the method return the current weather condition,5-day weather forecast and 8-day forecast soil datas

    return jsonify({'Current weather': current_weather_json,
                    'Five-days forecast weather': forecast_weather_json,
                    "Soil informations ": soil_info_json}), 200


#######################################################################################################################
# This is the second centric process

@app.route('/agri_info/<crop_name>', methods=['GET'])
@token_required
def agriInfo(user, crop_name):

    """" This endpoint used to generate the following information about crop by providing the crop name:
         -Detail crop description (Internal service)
         -Crop commodity exchange
         -Total production of the crop in Ethiopia
         -Import Export data of Coffee in Ethiopia

         In order to provide these informations, our service integrated with other external services.

         -United Nations Commodity Trade(External database Service)
            -This database offers comprehensive global data on imports and exports of commodities such as food, live animals, pharmaceuticals, metals, fuels and machinery.

         - United Nations Food and Agriculture(External database service)
            -This database offers global food and agricultural data, covering crop production, fertilizer consumption, use of land for agriculture, and livestock.

         -IntercontinentalExchange (External database service)
            - Commodity Market
            - The ICE Group is one of the largest futures exchanges in the world. It includes sub-exchanges in the US, Canada and Europe (including the NYBOT and CSC).
     """


    try:

        crop = Crop.query.filter_by(crop_name=crop_name).first()

        crop_data = {}
        crop_data['crop_id'] = crop.crop_id
        crop_data['crop_name'] = crop.crop_name
        crop_data['crop_description'] = crop.crop_description

        #but we are intested in the crop name to access other services
        crop = crop_data['crop_name']


         #Different url that allows to access the above services
        commodity_url = "https://www.quandl.com/api/v3/datasets/CHRIS/"
        tot_production_url = "https://www.quandl.com/api/v3/datasets/UFAO/"
        import_export_url = "https://www.quandl.com/api/v3/datasets/UCOM/"


#if the crop name is found in the database , then it return detial description, total prodution , commodity price and import export information.


        if crop == "Coffee":
            #This is commodity exchange informatin of Coffee
             coffee_commo_url = commodity_url + "ICE_KC1/data.json"
             coffee_commo_param ={'api_key': commodity_api_key, 'start_date':'2019-01-31'}
             coffee_commo_info_req = requests.get(coffee_commo_url, params=coffee_commo_param)
             coffee_commo_info_json = coffee_commo_info_req.json()

            #This is Total production infromation of Coffee in Ethiopia
             coffee_production_url = tot_production_url + "CR_GRCF_ETH/data.json"
             coffee_production_param = {'api_key': commodity_api_key, 'start_date': '2017-12-31'}
             coffee_production_info_req = requests.get(coffee_production_url, params=coffee_production_param)
             coffee_production_info_json = coffee_production_info_req.json()

            #This is the export data for coffee, tea and species

             coffee_import_export_url = import_export_url + "CTMS_ETH"
             coffee_import_export_param = {'api_key': commodity_api_key, 'column_index':'1'}
             coffee_import_export_req = requests.get(coffee_import_export_url, params=coffee_import_export_param)
             coffee_import_export_json = coffee_import_export_req.json()



             return jsonify({'Crop Description ': crop_data,
                             'Coffee Commdity Price': coffee_commo_info_json,
                             'Total production of Coffee in Ethiopia': coffee_production_info_json,
                             'Coffee export data': coffee_import_export_json}), 200

        elif crop =="Soybean":
            #This is commodity exchange informatin of Soybean
            soybean_commo_url = commodity_url + "CME_S1/data.json"
            soybean_commo_param = {'api_key': commodity_api_key, 'start_date': '2019-01-31'}
            soybean_commo_info_req = requests.get(soybean_commo_url, params=soybean_commo_param)
            soybean_commo_info_json = soybean_commo_info_req.json()

            #This is Total production infromation of Soybean in Ethiopia
            soybean_production_url = tot_production_url + "CR_SOYB_ETH/data.json"
            soybean_production_param = {'api_key': commodity_api_key, 'start_date': '2017-12-31'}
            soybean_production_info_req = requests.get(soybean_production_url, params=soybean_production_param)
            soybean_production_info_json = soybean_production_info_req.json()

            return jsonify({'Crop Description ': crop_data,
                            'Soybean Commdity Exchange': soybean_commo_info_json,
                            'Total production of Soybean in Ethiopia': soybean_production_info_json}), 200

        elif crop == "Corn":
            # This is commodity exchange information of Corn
            corn_commo_url = commodity_url + "CME_C1/data.json"
            corn_commo_param = {'api_key': commodity_api_key, 'start_date': '2019-01-31'}
            corn_commo_info_req = requests.get(corn_commo_url, params=corn_commo_param)
            corn_commo_info_json = corn_commo_info_req.json()

            # This is Total production information of Corn in Ethiopia
            corn_production_url = tot_production_url + "CR_CORN_ETH/data.json"
            corn_production_param = {'api_key': commodity_api_key, 'start_date': '2017-12-31'}
            corn_production_info_req = requests.get(corn_production_url, params=corn_production_param)
            corn_production_info_json = corn_production_info_req.json()

            return jsonify({'Crop Description ': crop_data,
                            'Corn Commdity Exchange': corn_commo_info_json,
                            'Total production of Corn in Ethiopia': corn_production_info_json}), 200
        elif crop == "Rice":
            # This is commodity exchange information of Rice
            rice_commo_url = commodity_url + "CME_RR1/data.json"
            rice_commo_param = {'api_key': commodity_api_key, 'start_date': '2019-01-31'}
            rice_commo_info_req = requests.get(rice_commo_url, params=rice_commo_param)
            rice_commo_info_json = rice_commo_info_req.json()

            # This is Total production information of Rice in Ethiopia
            rice_production_url = tot_production_url + "CR_PDRC_ETH/data.json"
            rice_production_param = {'api_key': commodity_api_key, 'start_date': '2017-12-31'}
            rice_production_info_req = requests.get(rice_production_url, params=rice_production_param)
            rice_production_info_json = rice_production_info_req.json()


            return jsonify({'Crop Description ': crop_data,
                            'Rice Commodity Exchange': rice_commo_info_json,
                            'Total production of Rice in Ethiopia': rice_production_info_json}),200

        elif crop == "Wheat":
            # This is commodity exchange information of Wheat
            wheat_commo_url = commodity_url + "CME_W1/data.json"
            wheat_commo_param = {'api_key': commodity_api_key, 'start_date': '2019-01-31'}
            wheat_commo_info_req = requests.get(wheat_commo_url, params=wheat_commo_param)
            wheat_commo_info_json = wheat_commo_info_req.json()

            # This is Total production information of Rice in Ethiopia
            wheat_production_url = tot_production_url + "CR_WHET_ETH/data.json"
            wheat_production_param = {'api_key': commodity_api_key, 'start_date': '2017-12-31'}
            wheat_production_info_req = requests.get(wheat_production_url, params=wheat_production_param)
            wheat_production_info_json = wheat_production_info_req.json()


            return jsonify({'Crop Description ': crop_data,
                            'Wheat Commodity Exchange': wheat_commo_info_json,
                            'Total production of Wheat in Ethiopia': wheat_production_info_json}), 200



    except:
             return jsonify({'Error': 'the requested crop not found in the database'}), 404




if __name__ =='__main__':
    app.run(debug=True)
