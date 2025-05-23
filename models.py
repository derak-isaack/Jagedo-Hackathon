from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum

class UserRole(Enum):
    ADMIN = 'admin'
    SERVICE_PROVIDER = 'service_provider'
    CUSTOMER = 'customer'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False) 
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    service_provider_profile = db.relationship('ServiceProviderProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    customer_profile = db.relationship('CustomerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    jobs_posted = db.relationship('Job', backref='customer', lazy='dynamic')
    applications = db.relationship('JobApplication', backref='applicant', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class ServiceProviderProfile(db.Model):
    __tablename__ = 'service_provider_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profession = db.Column(db.String(100), nullable=False)  # 'fundi', 'professional'
    specialization = db.Column(db.String(200))
    experience_years = db.Column(db.Integer)
    skills = db.Column(db.Text)  # JSON string of skills
    location = db.Column(db.String(200))
    hourly_rate = db.Column(db.Numeric(10, 2))
    bio = db.Column(db.Text)
    verification_status = db.Column(db.String(20), default='pending')  # 'pending', 'verified', 'rejected'
    ai_verification_score = db.Column(db.Float)
    ai_verification_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    documents = db.relationship('Document', backref='service_provider', lazy='dynamic', cascade='all, delete-orphan')

class CustomerProfile(db.Model):
    __tablename__ = 'customer_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(200))
    location = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    preferred_budget_range = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text)  # JSON string of required skills
    location = db.Column(db.String(200))
    budget_min = db.Column(db.Numeric(10, 2))
    budget_max = db.Column(db.Numeric(10, 2))
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default='open')  # 'open', 'in_progress', 'completed', 'cancelled'
    profession_type = db.Column(db.String(50))  # 'fundi', 'professional', 'both'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('JobApplication', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    matches = db.relationship('JobMatch', backref='job', lazy='dynamic', cascade='all, delete-orphan')

class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    proposed_rate = db.Column(db.Numeric(10, 2))
    estimated_duration = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected'
    ai_autofilled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobMatch(db.Model):
    __tablename__ = 'job_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_score = db.Column(db.Float, nullable=False)
    match_reasons = db.Column(db.Text)  # JSON string explaining match reasons
    is_notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    service_provider = db.relationship('User', foreign_keys=[service_provider_id])

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    service_provider_id = db.Column(db.Integer, db.ForeignKey('service_provider_profiles.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    document_type = db.Column(db.String(50))  # 'certificate', 'portfolio', 'id', 'resume'
    extracted_text = db.Column(db.Text)
    ai_analysis = db.Column(db.Text)  # JSON string of AI analysis results
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # 'job_match', 'application_status', 'approval', 'system'
    is_read = db.Column(db.Boolean, default=False)
    related_job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    related_job = db.relationship('Job', backref='notifications')