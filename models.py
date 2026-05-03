from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    future_opportunities = db.Column(db.String(200), nullable=False)
    max_applicants = db.Column(db.Integer)

    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)