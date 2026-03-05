from app import create_app, db
from app.models import User

def check_and_create_admin():
    app = create_app()
    with app.app_context():
        # List all users
        users = User.query.all()
        print(f"Current Users: {len(users)}")
        for u in users:
            print(f"ID: {u.id}, Email: {u.email}, Name: {u.name}, Role: {u.role}")
        
        # Check if an admin exists
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            print("No admin user found. Creating one...")
            admin = User(name='System Administrator', email='admin@bloodlife.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: email=admin@bloodlife.com password=admin123")
        else:
            print(f"Admin already exists: {admin_user.email}")

if __name__ == '__main__':
    check_and_create_admin()
