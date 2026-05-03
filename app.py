import uuid
from flask import Flask
from flask_cors import CORS
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from models import db, Admin, Opportunity
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_bcrypt import Bcrypt
from flask import request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

reset_tokens = {}  # temporary storage


@app.errorhandler(JWTExtendedException)
def handle_jwt_error(e):
    return {"message": str(e)}, 422

# ---------------- CONFIG ---------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = 'secretkey123'

db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


# ---------------- CREATE DB ---------------- #
with app.app_context():
    db.create_all()


# ---------------- SIGNUP ---------------- #
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json

    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')

    # validations
    if not full_name or not email or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters"}), 400

    # check existing user
    existing_user = Admin.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "Account already exists"}), 400

    # hash password
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = Admin(
        full_name=full_name,
        email=email,
        password=hashed_pw
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Signup successful"}), 201


# ---------------- LOGIN ---------------- #
@app.route('/login', methods=['POST'])
def login():
    data = request.json

    email = data.get('email')
    password = data.get('password')

    user = Admin.query.filter_by(email=email).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "token": token
    })


# ---------------- FORGOT PASSWORD ---------------- #
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')

    user = Admin.query.filter_by(email=email).first()

    if user:
        token = str(uuid.uuid4())
        reset_tokens[token] = {
            "user_id": user.id,
            "expires": datetime.utcnow() + timedelta(hours=1)
        }

        print(f"Reset link: http://localhost:5000/reset-password/{token}")

    return {"message": "If email exists, reset link sent"}


# ---------------- RESET PASSWORD ---------------- #
@app.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    data = request.json
    new_password = data.get('password')

    token_data = reset_tokens.get(token)

    if not token_data:
        return {"message": "Invalid or expired link"}, 400

    if datetime.utcnow() > token_data['expires']:
        return {"message": "Link expired"}, 400

    user = Admin.query.get(token_data['user_id'])
    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')

    db.session.commit()

    del reset_tokens[token]

    return {"message": "Password reset successful"}

# ---------------- CREATE OPPORTUNITY ---------------- #
@app.route('/opportunities', methods=['POST'])
@jwt_required()
def create_opportunity():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({"message": "Invalid JSON payload"}), 400

        required_fields = [
            "name", "duration", "start_date",
            "description", "skills", "category",
            "future_opportunities"
        ]

        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"{field} is required"}), 400

        opp = Opportunity(
            name=data['name'],
            duration=data['duration'],
            start_date=data['start_date'],
            description=data['description'],
            skills=data['skills'],
            category=data['category'],
            future_opportunities=data['future_opportunities'],
            max_applicants=data.get('max_applicants'),
            admin_id=int(user_id)
        )

        db.session.add(opp)
        db.session.commit()

        return jsonify({"message": "Opportunity created successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500


# ---------------- GET ALL OPPORTUNITIES ---------------- #
@app.route('/opportunities', methods=['GET'])
@jwt_required()
def get_opportunities():
    user_id = get_jwt_identity()

    opportunities = Opportunity.query.filter_by(admin_id=int(user_id)).all()

    result = []
    for o in opportunities:
        result.append({
            "id": o.id,
            "name": o.name,
            "duration": o.duration,
            "start_date": o.start_date,
            "description": o.description,
            "skills": o.skills,
            "category": o.category,
            "future_opportunities": o.future_opportunities,
            "max_applicants": o.max_applicants
        })

    return jsonify(result)


# ---------------- GET SINGLE OPPORTUNITY ---------------- #
@app.route('/opportunities/<int:id>', methods=['GET'])
@jwt_required()
def get_single_opportunity(id):
    user_id = get_jwt_identity()

    opp = Opportunity.query.get(id)

    if not opp or opp.admin_id != int(user_id):
        return jsonify({"message": "Not found"}), 404

    return jsonify({
        "id": opp.id,
        "name": opp.name,
        "duration": opp.duration,
        "start_date": opp.start_date,
        "description": opp.description,
        "skills": opp.skills,
        "category": opp.category,
        "future_opportunities": opp.future_opportunities,
        "max_applicants": opp.max_applicants
    })


# ---------------- UPDATE OPPORTUNITY ---------------- #
@app.route('/opportunities/<int:id>', methods=['PUT'])
@jwt_required()
def update_opportunity(id):
    user_id = get_jwt_identity()
    data = request.json

    opp = Opportunity.query.get(id)

    if not opp or opp.admin_id != int(user_id):
        return jsonify({"message": "Unauthorized"}), 403

    opp.name = data.get('name', opp.name)
    opp.duration = data.get('duration', opp.duration)
    opp.start_date = data.get('start_date', opp.start_date)
    opp.description = data.get('description', opp.description)
    opp.skills = data.get('skills', opp.skills)
    opp.category = data.get('category', opp.category)
    opp.future_opportunities = data.get('future_opportunities', opp.future_opportunities)
    opp.max_applicants = data.get('max_applicants', opp.max_applicants)

    db.session.commit()

    return jsonify({"message": "Updated successfully"})


# ---------------- DELETE OPPORTUNITY ---------------- #
@app.route('/opportunities/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_opportunity(id):
    user_id = get_jwt_identity()

    opp = Opportunity.query.get(id)

    if not opp or opp.admin_id != int(user_id):
        return jsonify({"message": "Unauthorized"}), 403

    db.session.delete(opp)
    db.session.commit()

    return jsonify({"message": "Deleted successfully"})


# ---------------- RUN SERVER ---------------- #
if __name__ == '__main__':
    app.run(debug=True)