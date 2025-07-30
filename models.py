from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import json

db = SQLAlchemy()

class User(db.Model):
    """Anonymous user model - no personal data stored"""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.String(100), nullable=False, index=True)
    department = db.Column(db.String(100), nullable=True, index=True)
    role_level = db.Column(db.String(50), nullable=True)  # junior, mid, senior, manager
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    responses = db.relationship('DailyResponse', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.id[:8]}... {self.department}>'

    def to_dict(self):
        return {
            'id': self.id,
            'department': self.department,
            'role_level': self.role_level,
            'created_at': self.created_at.isoformat(),
            'days_active': (datetime.utcnow() - self.created_at).days
        }

class DailyResponse(db.Model):
    """Daily questionnaire responses with AI analysis"""
    __tablename__ = 'daily_responses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)

    # Raw questionnaire data
    questions = db.Column(db.Text, nullable=False)  # JSON string of questions asked
    responses = db.Column(db.Text, nullable=False)  # JSON string of user responses

    # AI analysis results
    burnout_score = db.Column(db.Float, nullable=True, index=True)
    ai_analysis = db.Column(db.Text, nullable=True)  # JSON string of full AI analysis
    concerns = db.Column(db.Text, nullable=True)  # JSON array of identified concerns
    recommendations = db.Column(db.Text, nullable=True)  # JSON array of recommendations
    urgency_level = db.Column(db.String(20), nullable=True, index=True)  # low, medium, high

    # Metadata
    response_time_seconds = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<Response {self.id} - Score: {self.burnout_score}>'

    def get_responses_dict(self):
        """Parse responses JSON safely"""
        try:
            return json.loads(self.responses) if self.responses else {}
        except json.JSONDecodeError:
            return {}

    def get_analysis_dict(self):
        """Parse AI analysis JSON safely"""
        try:
            return json.loads(self.ai_analysis) if self.ai_analysis else {}
        except json.JSONDecodeError:
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'burnout_score': self.burnout_score,
            'urgency_level': self.urgency_level,
            'concerns': json.loads(self.concerns) if self.concerns else [],
            'recommendations': json.loads(self.recommendations) if self.recommendations else [],
            'created_at': self.created_at.isoformat(),
            'responses': self.get_responses_dict()
        }

class CompanyMetrics(db.Model):
    """Aggregated company-level analytics (no individual data)"""
    __tablename__ = 'company_metrics'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.String(100), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)

    # Aggregated metrics
    total_responses = db.Column(db.Integer, default=0)
    avg_burnout_score = db.Column(db.Float, nullable=True)
    high_risk_count = db.Column(db.Integer, default=0)
    medium_risk_count = db.Column(db.Integer, default=0)
    low_risk_count = db.Column(db.Integer, default=0)

    # Department breakdown (JSON)
    department_metrics = db.Column(db.Text, nullable=True)
    common_concerns = db.Column(db.Text, nullable=True)  # JSON array of top concerns

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Metrics {self.company_id} - {self.date}>'