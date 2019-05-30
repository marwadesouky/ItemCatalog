import string
import random
import requests
import json
import httplib2

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

# from flask_dance.contrib.google import make_google_blueprint, google
# from flask_login import logout_user

from flask import session as login_session

from database import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, asc
from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, make_response
app = Flask(__name__)

CLIENT_ID = json.loads(
	open('client_secrets.json', 'r').read())['web']['client_id']

CLIENT_SECRETS_FILE = "client_secrets.json"

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
API_SERVICE_NAME = 'drive'
API_VERSION = 'v2'


engine = create_engine(
    'sqlite:///catalogdb.db',
    connect_args={
        'check_same_thread': False},
         echo=True)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'])
                #    , picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    try:
        
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)

# @app.route('/gconnect', methods=['GET', 'POST'])
# def gconnect():

@app.route('/welcome')
def welcome():
	return render_template('welcome.html', picture=login_session['picture'], fullname=login_session['username'])
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]


    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect', methods=['GET', 'POST'])
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

@app.route('/gconnect', methods=['GET', 'POST'])
def gconnect():
    if request.method == 'POST':
        try:
            if login_session['state'] != request.args.get('state'):
                
                response = make_response(json.dumps('Invalid state parameter.'), 401)
                response.headers['Content-Type'] = 'application/json'
                print("step 1")
                return response

			# Retrieve the token sent by the client
            token = request.data
            print("step 2")

			# Request an access tocken from the google api
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), CLIENT_ID)
            print("step 3")
            url = (
        	'https://oauth2.googleapis.com/tokeninfo?id_token=%s'
                % token)
            h = httplib2.Http()
            result = json.loads(h.request(url, 'GET')[1])
            print("step 4")
            print(result['aud'])
			# If there was an error in the access token info, abort.
            if result.get('error') is not None:
                response = make_response(json.dumps(result.get('error')), 500)
                response.headers['Content-Type'] = 'application/json'
                return response
            print("step 5")
			# Verify that the access token is used for the intended user.
            user_google_id = idinfo['sub']
            if result['sub'] != user_google_id:
                response = make_response(
                    json.dumps("Token's user ID doesn't match given user ID."),	401)
                response.headers['Content-Type'] = 'application/json'
                return response
            print(result['sub'])
			# Verify that the access token is valid for this app.
            if result['aud'] != CLIENT_ID:
                print("step 5.5")
                response = make_response(json.dumps("Token's client ID does not match app's."), 401)
                
                print ("Token's client ID does not match app's.")
                response.headers['Content-Type'] = 'application/json'
                return response
                        
            print("step 6")
			# Check if the user is already logged in
            stored_access_token = login_session.get('access_token')
            stored_user_google_id = login_session.get('user_google_id')
            if stored_access_token is not None and user_google_id == stored_user_google_id:
                response = make_response(json.dumps('Current user is already connected.'), 200)
                response.headers['Content-Type'] = 'application/json'
                return response
            print("step 7")
			# Store the access token in the session for later use.
            login_session['access_token'] = idinfo
            login_session['user_google_id'] = user_google_id
			# Get user info
            login_session['username'] = idinfo['name']
            login_session['picture'] = idinfo['picture']
            login_session['email'] = idinfo['email']
            
            user_id = getUserID(idinfo['email'])
            
            if not user_id:
                user_id = createUser(login_session)
            
            login_session['user_id'] = user_id
            
            return 'Successful'
			
        except ValueError:
			# Invalid token
            print("value error")
            pass

# @app.route("/logout", methods=['GET', 'POST'])
# def logout():
#     token = blueprint.token["access_token"]
#     resp = google.post(
#         "https://accounts.google.com/o/oauth2/revoke",
#         params={"token": token},
#         headers={"Content-Type": "application/x-www-form-urlencoded"}
#     )
#     assert resp.ok, resp.text
#     logout_user()        # Delete Flask-Login's session cookie
#     del blueprint.token  # Delete OAuth token from storage
@app.route('/disconnect', methods=['GET', 'POST'])
def disconnect():
  """Revoke current user's token and reset their session."""
  # Only disconnect a connected user.
  access_token = login_session.get('access_token')
  
  if access_token is None:
    response = make_response(json.dumps('Current user not connected.'), 401)
    response.headers['Content-Type'] = 'application/json'
    return response

  # Execute HTTP GET request to revoke current token.
#   access_token = credentials.access_token
  url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
  h = httplib2.Http()
  result = h.request(url, 'GET')

  
  del login_session['access_token']
#   del login_session['gplus_id']
  del login_session['username']
  del login_session['email']
  del login_session['picture']

  response = make_response(json.dumps('Successfully disconnected.'), 200)
  response.headers['Content-Type'] = 'application/json'
  
  return response

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/brands', methods=['GET','POST'])
def showBrands():
    brands = session.query(Brand).all()
    # .order_by(asc(Brand.name))
    if 'username' not in login_session:
        return render_template('publicbrands.html', brands=brands)
    else:
        return render_template('brands.html', brands=brands)

@app.route('/brands/new', methods=['GET','POST'])
def newBrand():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newBrand = Brand(name = request.form['name'], user_id=login_session['user_id'])
        session.add(newBrand)
        flash('New Brand %s Successfully Created' % newBrand.name)
        session.commit()
        return redirect(url_for('showBrands'))
    else:
        return render_template('newbrand.html')

@app.route('/brands/<int:brand_id>/edit')
def editBrand(brand_id):
    if 'username' not in login_session:
            return redirect('/login')
    editedBrand = session.query(Brand).filter_by(id = brand_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedBrand.name = request.form['name']
            session.add(editBrand)
            flash('Brand Successfully Edited %s' % editedBrand.name)
            session.commit()
            return redirect(url_for('showBrands'))
    else:
        return render_template('editbrand.html', brand = editedBrand)

@app.route('/brands/<int:brand_id>/delete')
def deleteBrand(brand_id):
    if 'username' not in login_session:
            return redirect('/login')
    deletedBrand = session.query(Brand).filter_by(id=brand_id).one()
    session.delete(deletedBrand)
    flash('Brand %s Successfully Edited ' % deletedBrand.name)
    session.commit()

    return redirect(url_for('showBrands'))

@app.route('/cars')
def allCars():
    cars = session.query(Car).all()
    return render_template('allcars.html', cars=cars)

@app.route('/brand/<int:brand_id>/cars')
def showCars(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    cars = session.query(Car).filter_by(brand_id=brand_id).all()
    
    if 'username' not in login_session:
        return render_template('carspublic.html', cars=cars)
    else:
        return render_template('cars.html', brand=brand, cars=cars)

@app.route('/brand/<int:brand_id>/car/<int:car_id>')
def showCar(brand_id, car_id):
    if 'username' not in login_session:
        return render_template('carpublic.html', brand=brand, car=car, specs=specs, highlights=highlights)

    brand = session.query(Brand).filter_by(id=brand_id).one()
    car = session.query(Car).filter_by(id=car_id).one()
    specs = json.loads(car.specs)
    highlights = json.loads(car.highlights)
    
    return render_template('car.html', brand=brand, car=car, specs=specs, highlights=highlights)

@app.route('/brand/<int:brand_id>/car/new', methods=['GET', 'POST'])
def newCar(brand_id):
    if 'username' not in login_session:
        return redirect('/login')

    brand = session.query(Brand).filter_by(id=brand_id).one()
    if request.method == 'GET':
        return render_template('newcar.html', brand=brand)

    newcar = request.form

    if name is None:
        return "No new car"
    
    car = Car(name=name, user_id=login_session['user_id'], brand_id=brand_id)
    car.description = newcar['description']
    car.price = newcar['price']
    car.condition = newcar['condition']
    car.model = newcar['model']
    car.color = newcar['color']
    car.specs = json.dumps(newcar.getlist("specs"))
    car.highlights = json.dumps(newcar.getlist("highlights"))
    session.add(car)
    session.commit()

    return render_template('car.html', brand=brand, car=car)

@app.route('/brand/<int:brand_id>/car/<int:car_id>/edit', methods=['GET', 'POST'])
def editCar(brand_id, car_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    car = session.query(Car).filter_by(id=car_id).one()
    if request.method == 'GET':
        return render_template('editcar.html', brand=brand, car=car)
    
    editedcar = request.form
    if(editedcar['name']): car.name = editedcar['name']
    if(editedcar['description']): car.description = editedcar['description']
    if(editedcar['price']): car.price = editedcar['price']
    if(editedcar['condition']): car.condition = editedcar['condition']
    if(editedcar['model']): car.model = editedcar['model']
    if(editedcar['specs']): car.specs = editedcar['specs']
    if(editedcar['highlights']): car.highlights = editedcar['highlights']

    session.add(car)
    session.commit()

    return redirect('/cars', brand_id=brand_id, car_id=car_id)

@app.route('/brand/<int:brand_id>/car/<int:car_id>/delete', methods=['GET','POST'])
def deleteCar(brand_id, car_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    car = session.query(Car).filter_by(id=car_id).one()

    session.delete(car)
    flash('Brand %s Successfully Edited ' % car.name)              
    session.commit()

    return redirect('/cars', brand_id=brand_id)

@app.route('/test', methods=['GET','POST'])
def testfunc():
    if request.method == 'GET':
        return render_template('test.html')
    
    form = request.form
    dic = form.getlist("specs")
    print dic
    specs=form['specs']

    print form
    for key in form:
        print key
    print "specs = ", specs
    
    return redirect('/test')

@app.route('/brands/JSON')
def restaurantsJSON():
		brands = session.query(Brand).all()
		return jsonify(Brands=[b.serialize for b in brands])


@app.route('/brand/<int:brand_id>/car/JSON')
def restaurantMenuJSON(restaurant_id):
		brand = session.query(Restaurant).filter_by(id = restaurant_id).one()
		cars = session.query(Car).filter_by(brand_id=brand_id).all()
		return jsonify(Car=[i.serialize for i in cars])


@app.route('/brand/<int:brand_id>/car/<int:car_id>/JSON')
def menuItemJSON(brand_id, car_id):
		car = session.query(Car).filter_by(id=car_id).one()
		return jsonify(Car=car.serialize)



if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 8000)