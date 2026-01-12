from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    habits = db.relationship('Habit', backref='owner', lazy=True)
    subjects = db.relationship('Subject', backref='owner', lazy=True)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    is_recurring = db.Column(db.Boolean, default=True)  # True = Daily, False = One-time
    target_date = db.Column(db.Date, nullable=True)     # For one-time habits
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    logs = db.relationship('DailyLog', backref='habit', lazy=True)

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    completed = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('habit_id', 'date', name='unique_habit_date'),
    )

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attendance_records = db.relationship('AttendanceRecord', backref='subject', lazy=True, cascade='all, delete-orphan')

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), nullable=False)  # 'Present' or 'Absent'

    __table_args__ = (
        db.UniqueConstraint('subject_id', 'date', name='unique_subject_date'),
    )
