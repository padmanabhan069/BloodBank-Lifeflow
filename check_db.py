from app import create_app, db
from app.models import User, DonorProfile

app = create_app()
with app.app_context():
    users = User.query.all()
    profiles = DonorProfile.query.all()
    print(f"Total Users: {len(users)}")
    for u in users:
        print(f"User ID: {u.id}, Name: {u.name}, Blocked: {u.is_blocked}")
    print(f"Total Profiles: {len(profiles)}")
    for p in profiles:
        print(f"Profile ID: {p.id}, User ID: {p.user_id}, Name: {p.user.name}")
