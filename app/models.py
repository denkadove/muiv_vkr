from datetime import datetime
from flask_login import UserMixin
from sqlalchemy.orm import validates
from app import db

class UserGroup(db.Model):
    __tablename__ = "user_groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey("user_groups.id"), nullable=True)
    group = db.relationship("UserGroup", backref="users")
    created = db.Column(db.DateTime, default=datetime.utcnow)
