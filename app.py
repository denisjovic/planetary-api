from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float
from flask_marshmallow import Marshmallow
import os
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_mail import Mail, Message

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'planets.db')
app.config['JWT_SECRET_KEY'] = 'supersecret'
app.config['MAIL_SERVER'] = 'smtp.mailtrap.io'
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = '688c780f5a9a15'
app.config['MAIL_PASSWORD'] = '0452febd66f1e7'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
mail = Mail(app)


# CLI commands for create/delete/populate db
@app.cli.command('db_create')
def db_create():
    db.create_all()
    print('DB created!')


@app.cli.command('db_drop')
def db_drop():
    db.drop_all()
    print("DB deleted!")


@app.cli.command('db_seed')
def db_seed():
    mercury = Planet(name='Mercury', type='Class D', home_star='Sol', mass=3.258233, radius=1516, distance=35.98e6)
    venus = Planet(name='Venus', type='Class K', home_star='Sol', mass=4.2898233, radius=3760, distance=67.24e6)
    earth = Planet(name='Earth', type='Class M', home_star='Sol', mass=5.972233, radius=3959, distance=92.53e6)

    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)

    test_user = User(first='Denis', last='Jovic', email='denisjovic@email.com', password='12345')
    db.session.add(test_user)

    db.session.commit()
    print('DB seeded')


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/simple')
def simple():
    return jsonify(message='Hello from planetary API!', poruka='nova porika?')


@app.route('/not_found')
def not_found():
    return jsonify(message='not found'), 404


@app.route('/params')
def params():
    name = request.args.get('name')
    age = int(request.args.get('age'))
    if age < 18:
        return jsonify(msg="You are not old enough, fuck off")
    return jsonify(msg=f"Welcome, {name}")


@app.route('/url_vars/<string:name>/<int:age>')
def url_vars(name: str, age: int):
    if age < 21:
        return jsonify(msg="You are not old enough, fuck off man")
    return jsonify(msg=f"Welcome aboard, {name}")


@app.route('/planets', methods=['GET'])
def planets():
    planets_list = Planet.query.all()
    result = planets_schema.dump(planets_list)
    return jsonify(result)


@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    test = User.query.filter_by(email=email).first()
    if test:
        return jsonify(msg='Email already exists'), 409
    first = request.form['first']
    last = request.form['last']
    password = request.form['password']
    user = User(first=first, last=last, email=email, password=password)
    db.session.add(user)
    db.session.commit()
    return jsonify(msg='User created!'), 201


@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        email = request.json['email']
        password = request.json['password']
    else:
        email = request.form['email']
        password = request.form['password']
    test = User.query.filter_by(email=email, password=password).first()
    if test:
        access_token = create_access_token(identity=email)
        return jsonify(msg='login success', access_token=access_token)
    return jsonify(msg='login failed'), 401


@app.route('/get_password/<string:email>', methods=['GET'])
def get_password(email: str):
    user = User.query.filter_by(email=email).first()
    if user:
        msg = Message("You planetary API password is " + user.password,
                      sender="admin@planetary_api.com",
                      recipients=[email])
        mail.send(msg)
        return jsonify(message="Password sent to " + email)
    else:
        return jsonify(message="Email does not exist"), 401


@app.route('/get_planet/<int:id>', methods=['GET'])
def get_planet(id: int):
    planet = Planet.query.filter_by(id=id).first()
    if planet:
        result = planet_schema.dump(planet)
        return jsonify(result)
    return jsonify(msg="Planet does not exist!"), 404


@app.route('/add_planet', methods=['POST'])
@jwt_required
def add_planet():
    planet_name = request.form['name']
    test = Planet.query.filter_by(name=planet_name).first()
    if test:
        return jsonify(msg='Planet already exists')
    type = request.form['type']
    mass = request.form['mass']
    home_star = request.form['home_star']
    radius = request.form['radius']
    distance = request.form['distance']

    new_planet = Planet(name=planet_name, type=type, mass=mass, home_star=home_star, radius=radius, distance=distance)
    db.session.add(new_planet)
    db.session.commit()
    return jsonify(msg='Planet added!'), 201


@app.route('/update', methods=['PUT'])
@jwt_required
def update():
    planet_id = int(request.form['id'])
    planet = Planet.query.filter_by(id=planet_id).first()
    if planet:
        planet.name = request.form['name']
        planet.radius = float(request.form['radius'])
        planet.mass = float(request.form['mass'])
        planet.distance = float(request.form['distance'])
        planet.home_star = request.form['home_star']
        planet.type = request.form['type']
        # when updating entry, we don't need to use db.session.add()
        db.session.commit()
        return jsonify(msg="Planet successfully updated!"), 202
    return jsonify(msg="Planet does not exist"), 404


@app.route('/delete/<int:id>', methods=['DELETE'])
@jwt_required
def delete(id: int):
    planet = Planet.query.filter_by(id=id).first()
    if planet:
        db.session.delete(planet)
        db.session.commit()
        return jsonify(msg="Planet deleted!"), 202
    return jsonify(msg="Can't delete what's not there!"), 404


# database models
class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first = Column(String)
    last = Column(String)
    email = Column(String, unique=True)
    password = Column(String)


class Planet(db.Model):
    __tablename__ = 'planets'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    home_star = Column(String)
    mass = Column(Float)
    radius = Column(Float)
    distance = Column(Float)


# using Marshmellow for serialization -> turning text to json
class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first', 'last', 'email', 'password')


class PlanetSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'type', 'home_star', 'mass', 'radius', 'distance')


# creating instances of marsh classes
user_schema = UserSchema()
users_schema = UserSchema(many=True)

planet_schema = PlanetSchema()
planets_schema = PlanetSchema(many=True)

if __name__ == '__main__':
    app.run()
