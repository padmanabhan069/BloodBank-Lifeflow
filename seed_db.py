from app import create_app, db
from app.models import User, DonorProfile
from datetime import date

def seed_donors():
    app = create_app()
    with app.app_context():
        # Create a few test users
        donors_data = [
            {'name': 'John Doe', 'email': 'john@example.com', 'bg': 'A+', 'loc': 'New York'},
            {'name': 'Jane Smith', 'email': 'jane@example.com', 'bg': 'O-', 'loc': 'Los Angeles'},
            {'name': 'Mike Ross', 'email': 'mike@example.com', 'bg': 'B+', 'loc': 'Chicago'},
        ]
        
        for data in donors_data:
            user = User.query.filter_by(email=data['email']).first()
            if not user:
                user = User(name=data['name'], email=data['email'])
                user.set_password('password123')
                db.session.add(user)
                db.session.flush()
                
                profile = DonorProfile(
                    user_id=user.id,
                    blood_group=data['bg'],
                    location=data['loc'],
                    city=data['loc'],
                    is_available=True,
                    is_platelet_donor=True,
                    dob=date(1990, 1, 1),
                    weight=70,
                    height=175
                )
                profile.compute_rank_score()
                db.session.add(profile)
        
        db.session.commit()
        print("Seed data added!")

if __name__ == '__main__':
    seed_donors()
