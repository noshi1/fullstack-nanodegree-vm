"""from geocode import getGeocodeLocation"""
import json
import httplib2
import datetime
import os
from flask import session as login_session
import random
import string

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from models import User, Categories, Items, Base
from sqlalchemy.orm import load_only

#import for user login and authentication
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from flask import Flask, render_template, url_for
from flask import request, redirect, flash, jsonify
from login_decorator import login_required

app = Flask(__name__)

""" Create session and connect to DB."""
engine = create_engine('sqlite:///catalog2.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"


@app.route('/login')
def showLogin():
    """ Create anti-forgery state token"""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """ facebook login code """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

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
        Due to the formatting for the result from the server token
        exchange we have to split the token first on commas and
        select the first index which gives us the key : value
        for the server access token then we split it on colons
        to pull out the actual token valueand replace the remaining
        quotes with nothing so that it can be used directly in the graph
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
    output += """ <" style = "width: 300px;
    height: 300px;border-radius: 150px;
    -webkit-border-radius: 150px;-moz-border-radius: 150px;"> """

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    """ this code will logout facebook account """
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """Gmail login code """
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
                                json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exist if not create new user
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
    """output += ' " style = "width: 300px; height: 300px;border-radius:
    150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">"""
    flash("You are now logged in as %s" % login_session['username'])
    print "done!"
    return output


def createUser(login_session):
    """User Helper Functions to create get user info"""
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
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


@app.route('/gdisconnect')
def gdisconnect():
        """Only disconnect a connected user."""
        access_token = login_session.get('access_token')

        if access_token is None:
            response = make_response(json.dumps('Current user not connected.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
        h = httplib2.Http()
        result = h.request(url, 'GET')[0]
        if result['status'] == '200':
            # Reset the user's sesson.
            del login_session['access_token']
            del login_session['gplus_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']

        # response = make_response(json.dumps('Successfully disconnected.'), 200)
        # response.headers['Content-Type'] = 'application/json'
        if 'username' not in login_session:
            response = redirect(url_for('showCatalog'))
            return response
        else:
            # For whatever reason, the given token was invalid.
            response = make_response(json.dumps('Failed to revoke token for given user.', 400))
            response.headers['Content-Type'] = 'application/json'
            return response


@app.context_processor
def override_url_for():
    """ this snipped code will reload css and update it """
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


@app.route('/')
@app.route('/catalog')
def showCatalog():
    """Homepage"""
    categories = session.query(Categories).all()
    """category_ids = session.query(Categories.id).all()"""
    items = session.query(Items).order_by(desc(Items.date)).limit(5)
    if "username" not in login_session:
        return render_template('categories.html', categories=categories, items=items)
    else:
        return render_template('catalog.html', categories=categories, items=items)


@app.route('/catalog/new', methods=['GET', 'POST'])
@login_required
def newCategory():
    """add new category"""
    categories = session.query(Categories).all()
    if request.method == 'POST':
        newCategory = Categories(name=request.form['name'], user_id=login_session['user_id'])
        session.add(newCategory)
        session.commit()
        flash("New category is added %s " % newCategory.name)
        return redirect(url_for('showCatalog'))
    else:
        return render_template('addCategory.html', categories=categories)


@app.route('/catalog/<path:category_name>/edit',  methods=['GET', 'POST'])
@login_required
def editCategory(category_name):
    """edit existing category"""
    categories = session.query(Categories).all()
    editcategory = session.query(Categories).filter_by(name=category_name).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(editcategory.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash ("You cannot edit this Category. This Category belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
        if request.form['name']:
            editcategory.name = request.form['name']
            session.add(editcategory)
            session.commit()
            flash("Category is updated successfully to %s " % editcategory.name)
            return redirect(url_for('showCatalog'))
    return render_template('updateCategory.html', categories=categories, editcategory=editcategory, category_name=category_name)


@app.route('/catalog/<path:category_name>/delete', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_name):
    """delete a category"""
    categories = session.query(Categories).all()
    deletecategory = session.query(Categories).filter_by(name=category_name).first()
    # See if the logged in user is the owner of item
    creator = getUserInfo(deletecategory.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash ("You cannot delete this Category. This Category belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
            session.delete(deletecategory)
            session.commit()
            flash(" %s category is deleted successfully" % deletecategory.name)
            return redirect(url_for('showCatalog'))
    return render_template('deleteCategory.html', categories=categories, deletecategory=deletecategory, category_name=category_name)


@app.route('/catalog/<int:category_id>/items')
def showCategoryItems(category_id):
    """show a specific category's items"""
    categories = session.query(Categories).all()
    category = session.query(Categories).filter_by(id=category_id).first()
    items = session.query(Items).filter_by(category_id=category_id).all()
    creator = getUserInfo(category.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicItems.html', categories=categories, category=category, items=items)
    else:
        return render_template('categoryItems.html', categories=categories, category=category, items=items)


@app.route('/catalog/newItem', methods=['GET', 'POST'])
@login_required
def newCategoryItem():
    """add new items"""
    categories = session.query(Categories).all()
    if request.method == 'POST':
        newItem = Items(
            name=request.form['name'],
            description=request.form['description'],
            date=datetime.datetime.now(),
            category_id=request.form['category'],
            user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("New Item added: %s " % newItem.name)
        return redirect(url_for('showCatalog'))
    return render_template('addItem.html', categories=categories)


@app.route('/catalog/<int:category_id>/<int:item_id>/')
def showItem(category_id, item_id):
    """show delails of a specific item"""
    categories = session.query(Categories).all()
    category = session.query(Categories).filter_by(id=category_id).one()
    itemdetails = session.query(Items).filter_by(id=item_id).one()
    creator = getUserInfo(category.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicItemDetails.html', categories=categories, item_id=item_id, item=itemdetails, category_id=category_id, category=category)
    return render_template('showItem.html', categories=categories, item_id=item_id, item=itemdetails, category_id=category_id, category=category)


@app.route('/catalog/<int:category_id>/<int:item_id>/edit/', methods=['GET', 'POST'])
@login_required
def editItem(category_id, item_id):
    """edit an item"""
    categories = session.query(Categories).all()
    category = session.query(Categories).filter_by(id=category_id).one()
    editItem = session.query(Items).filter_by(id=item_id).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(editItem.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash ("You cannot edit this Category. This Category belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    # Post method
    if request.method == 'POST':
        if request.form['name']:
            editItem.name = request.form['name']
            date = datetime.datetime.now()
        if request.form['description']:
            editItem.description = request.form['description']
        session.add(editItem)
        session.commit()
        flash(" %s : Item updated successfully " % editItem.name)
        return redirect(url_for('showCategoryItems', category_id=category.id))
    return render_template('updateItem.html', categories=categories, category_id=category_id, item_id=item_id, item=editItem)


@app.route('/catalog/<int:category_id>/<int:item_id>/delete', methods=['GET', 'POST'])
@login_required
def deleteItem(category_id, item_id):
    """delete an item"""
    categories = session.query(Categories).all()
    category = session.query(Categories).filter_by(id=category_id).one()
    deletedItem = session.query(Items).filter_by(id=item_id).one()
    # See if the logged in user is the owner of item
    creator = getUserInfo(deletedItem.user_id)
    user = getUserInfo(login_session['user_id'])
    # If logged in user != item owner redirect them
    if creator.id != login_session['user_id']:
        flash ("You cannot edit this Category. This Category belongs to %s" % creator.name)
        return redirect(url_for('showCatalog'))
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash(" %s : Item is deleted successfully " % deletedItem.name)
        return redirect(url_for('showCategoryItems', category_id=category.id))
    return render_template('deleteItem.html', categories=categories, category_id=category_id, item_id=item_id, deletedItem=deletedItem)


"""Making an api endpoints"""


@app.route('/catalog/json')
def showCatalogJson():
    categories = session.query(Categories).all()
    return jsonify(categories=[c.serialize for c in categories])


@app.route('/catalog/<int:category_id>/items/json')
def showCategoryJson(category_id):
    items = session.query(Items).filter_by(category_id=category_id)
    return jsonify(items=[i.serialize for i in items])


@app.route('/catalog/<int:category_id>/<int:item_id>/json')
def showItemJson(category_id, item_id):
    categoryItem = session.query(Items).filter_by(id=item_id).one()
    return jsonify(categoryItem=[categoryItem.serialize])


@app.route('/catalog/users/json')
def showUsersJson():
    users = session.query(User).all()
    return jsonify(users=[u.serialize for u in users])


if __name__ == '__main__':
    app.secret_key = 'catalog_secret_key1'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
