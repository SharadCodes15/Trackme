#!/usr/bin/env python
"""
Seed script to populate database with subjects for the Student Corner module.
Run this script to add the initial subjects to the database.
"""
from app import app
from models import db, User, Subject

def seed_subjects():
    """Seed the database with predefined subjects."""
    with app.app_context():
        # Get or create the demo user
        user = User.query.first()
        if not user:
            user = User(username='demo_user')
            db.session.add(user)
            db.session.commit()
            print("Created demo user.")
        
        # Define subjects from timetable
        subject_names = [
            'M-II', 'DSPD-I', 'DCMP', 'BEE', 'DMGT', 'HISP-II',
            'BEE (LAB)', 'DSPD-I (LAB)', 'DCMP (LAB)'
        ]
        
        # Add subjects if they don't exist
        added_count = 0
        for name in subject_names:
            existing = Subject.query.filter_by(name=name, user_id=user.id).first()
            if not existing:
                subject = Subject(name=name, user_id=user.id)
                db.session.add(subject)
                added_count += 1
                print(f"Added subject: {name}")
            else:
                print(f"Subject already exists: {name}")
        
        db.session.commit()
        print(f"\nSeeding complete! Added {added_count} new subjects.")
        print(f"Total subjects in database: {Subject.query.filter_by(user_id=user.id).count()}")

if __name__ == '__main__':
    seed_subjects()
