from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False) # 'Hackathon', 'Competition', 'Conference'
    source_platform = db.Column(db.String(100), nullable=False) # e.g., 'Unstop', 'Devfolio', 'IEEE'
    url = db.Column(db.String(500), nullable=False)
    
    # Missing fields from spec
    organizer = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    eligibility = db.Column(db.String(200), nullable=True)
    
    # Deadlines
    registration_deadline = db.Column(db.DateTime, nullable=True)
    submission_deadline = db.Column(db.DateTime, nullable=True)
    notification_date = db.Column(db.DateTime, nullable=True)
    camera_ready_deadline = db.Column(db.DateTime, nullable=True)
    
    # Verification
    is_scopus_indexed = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'source_platform': self.source_platform,
            'url': self.url,
            'registration_deadline': self.registration_deadline.strftime('%Y-%m-%d %H:%M') if self.registration_deadline else None,
            'submission_deadline': self.submission_deadline.strftime('%Y-%m-%d %H:%M') if self.submission_deadline else None,
            'notification_date': self.notification_date.strftime('%Y-%m-%d %H:%M') if self.notification_date else None,
            'camera_ready_deadline': self.camera_ready_deadline.strftime('%Y-%m-%d %H:%M') if self.camera_ready_deadline else None,
            'is_scopus_indexed': self.is_scopus_indexed,
            'is_verified': self.is_verified
        }

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, unique=True)
    
    # Comma-separated list of interests (e.g. "AI,Web3,Hackathon")
    interests = db.Column(db.String(200), nullable=True)
    branch = db.Column(db.String(100), nullable=True)
    
    # Missing fields from spec
    preferred_types = db.Column(db.String(200), nullable=True) # e.g. "Hackathon,Conference"
    whatsapp_enabled = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AlertHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunity.id'), nullable=False)
    alert_type = db.Column(db.String(50)) # 'new', 'registration_7_days', 'submission_24_hours'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('alerts', lazy=True))
    opportunity = db.relationship('Opportunity', backref=db.backref('alerts', lazy=True))
