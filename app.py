from flask import Flask, render_template, request, jsonify, session, Response
from flask_sqlalchemy import SQLAlchemy
import os
import json
import io
import csv
import logging
from datetime import datetime, timedelta
import uuid
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bloom.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.String(100), nullable=False, index=True)
    department = db.Column(db.String(100), nullable=True, index=True)
    role_level = db.Column(db.String(50), nullable=True)
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

# ==================== BASIC ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/company-dashboard')
def company_dashboard():
    return render_template('company_dashboard.html')

@app.route('/health')
def health():
    """Health check endpoint with system statistics"""
    try:
        # Test database connection
        with app.app_context():
            result = db.session.execute(db.text('SELECT 1')).scalar()
            db_status = 'connected' if result == 1 else 'error'

        user_count = User.query.count()
        response_count = DailyResponse.query.count()

        return jsonify({
            'status': 'healthy',
            'message': 'Bloom is running! 🌸',
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'statistics': {
                'total_users': user_count,
                'total_responses': response_count,
                'uptime': 'Running since server start'
            },
            'features': {
                'user_registration': 'available',
                'data_export': 'available',
                'company_analytics': 'available',
                'emergency_help': 'available'
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('index.html')

    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('company_id'):
            return jsonify({'success': False, 'error': 'Company ID is required'}), 400

        # Create new user
        user = User(
            company_id=data['company_id'].lower().strip(),
            department=data.get('department', '').lower().strip() if data.get('department') else None,
            role_level=data.get('role_level', '').lower().strip() if data.get('role_level') else None
        )

        db.session.add(user)
        db.session.commit()

        # Set session
        session['user_id'] = user.id
        session['company_id'] = user.company_id

        logger.info(f"New user registered: {user.id[:8]}... in {user.company_id}")

        return jsonify({
            'success': True,
            'message': 'Registration successful!',
            'redirect': '/questionnaire'
        })

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Registration failed. Please try again.'
        }), 500

# ==================== QUESTION GENERATION ====================

def get_fallback_questions():
    """Get fallback questions when AI is not available"""
    return [
        {
            'id': 1,
            'question': 'How would you rate your energy level today?',
            'type': 'scale',
            'scale_label': '1 = Very Low Energy,10 = Very High Energy',
            'category': 'energy'
        },
        {
            'id': 2,
            'question': 'How satisfied do you feel with your work today?',
            'type': 'scale',
            'scale_label': '1 = Very Dissatisfied,10 = Very Satisfied',
            'category': 'satisfaction'
        },
        {
            'id': 3,
            'question': 'How stressed do you feel right now?',
            'type': 'scale',
            'scale_label': '1 = Not Stressed,10 = Extremely Stressed',
            'category': 'stress'
        },
        {
            'id': 4,
            'question': 'How well are you able to balance work and personal life?',
            'type': 'scale',
            'scale_label': '1 = Poor Balance,10 = Excellent Balance',
            'category': 'balance'
        },
        {
            'id': 5,
            'question': 'Is there anything specific that made work challenging today?',
            'type': 'text',
            'placeholder': 'Share anything that affected your well-being today...',
            'category': 'challenges'
        }
    ]

@app.route('/api/questions')
def get_questions():
    """Generate personalized questions for user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Get user info for personalization
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update last active
        user.last_active = datetime.utcnow()
        db.session.commit()

        # For now, use fallback questions
        # In production, this would call AI service to generate personalized questions
        questions = get_fallback_questions()

        # Could personalize based on user's previous responses, department, etc.
        # For example, add department-specific questions
        if user.department == 'engineering':
            questions.append({
                'id': 6,
                'question': 'How manageable is your current coding workload?',
                'type': 'scale',
                'scale_label': '1 = Overwhelming,10 = Very Manageable',
                'category': 'workload'
            })
        elif user.department == 'sales':
            questions.append({
                'id': 6,
                'question': 'How confident do you feel about meeting your targets?',
                'type': 'scale',
                'scale_label': '1 = Not Confident,10 = Very Confident',
                'category': 'confidence'
            })

        # Randomize question order for variety
        random.shuffle(questions)
        questions = questions[:5]  # Limit to 5 questions

        return jsonify({
            'questions': questions,
            'user_context': {
                'department': user.department,
                'days_active': (datetime.utcnow() - user.created_at).days
            }
        })

    except Exception as e:
        logger.error(f"Question generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate questions'}), 500

# ==================== RESPONSE SUBMISSION ====================

def analyze_responses(questions, responses):
    """Analyze user responses and generate insights"""
    try:
        # Calculate burnout score based on responses
        total_score = 0
        scale_count = 0
        stress_factors = []

        for i, question in enumerate(questions):
            response = responses[i] if i < len(responses) else None

            if question['type'] == 'scale' and response is not None:
                scale_value = float(response)
                scale_count += 1

                # Convert scale responses to burnout indicators
                if question['category'] in ['stress']:
                    # Higher stress = higher burnout score
                    total_score += scale_value * 10
                elif question['category'] in ['energy', 'satisfaction', 'balance']:
                    # Lower energy/satisfaction/balance = higher burnout score
                    total_score += (11 - scale_value) * 10
                else:
                    # General case - lower rating = higher burnout
                    total_score += (11 - scale_value) * 10

            elif question['type'] == 'text' and response:
                # Analyze text for stress indicators
                stress_keywords = ['overwhelmed', 'stressed', 'tired', 'burned', 'exhausted',
                                   'pressure', 'deadline', 'too much', 'can\'t cope']
                response_lower = response.lower()

                for keyword in stress_keywords:
                    if keyword in response_lower:
                        stress_factors.append(f"Mentioned feeling {keyword}")
                        total_score += 15  # Add to burnout score

        # Calculate final score (0-100, where higher = more burnout risk)
        if scale_count > 0:
            burnout_score = min(100, total_score / scale_count)
        else:
            burnout_score = 50  # Default neutral score

        # Determine urgency level
        if burnout_score >= 70:
            urgency = 'high'
        elif burnout_score >= 40:
            urgency = 'medium'
        else:
            urgency = 'low'

        # Generate concerns and recommendations
        concerns = []
        recommendations = []

        if burnout_score >= 70:
            concerns.extend(['High stress levels detected', 'Risk of burnout'])
            recommendations.extend([
                {'type': 'immediate', 'action': 'Take a break and practice deep breathing'},
                {'type': 'urgent', 'action': 'Consider speaking with a manager about workload'},
                {'type': 'support', 'action': 'Reach out to employee assistance program'}
            ])
        elif burnout_score >= 40:
            concerns.append('Moderate stress levels')
            recommendations.extend([
                {'type': 'immediate', 'action': 'Take a 10-minute mindfulness break'},
                {'type': 'preventive', 'action': 'Schedule regular breaks throughout the day'},
                {'type': 'module', 'title': 'Stress management techniques'}
            ])
        else:
            recommendations.extend([
                {'type': 'maintenance', 'action': 'Keep up the good work!'},
                {'type': 'preventive', 'action': 'Continue daily check-ins'},
                {'type': 'growth', 'action': 'Share wellness tips with colleagues'}
            ])

        # Add text-based concerns
        concerns.extend(stress_factors)

        analysis = {
            'score': round(burnout_score, 1),
            'urgency': urgency,
            'concerns': concerns,
            'recommendations': recommendations,
            'summary': generate_summary(burnout_score, concerns, urgency)
        }

        return analysis

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        # Return safe fallback analysis
        return {
            'score': 50.0,
            'urgency': 'medium',
            'concerns': ['Unable to complete full analysis'],
            'recommendations': [
                {'type': 'immediate', 'action': 'Take a moment to reflect on your wellbeing'},
                {'type': 'follow-up', 'action': 'Try completing another check-in tomorrow'}
            ],
            'summary': 'Analysis completed with limited data. Continue daily check-ins for better insights.'
        }

def generate_summary(score, concerns, urgency):
    """Generate a summary based on analysis results"""
    if score >= 70:
        return "Your responses indicate high stress levels. It's important to take immediate action to prevent burnout. Consider reaching out for support."
    elif score >= 40:
        return "Your wellbeing shows some areas of concern. Taking proactive steps now can help prevent more serious issues."
    else:
        return "You're managing well overall! Keep up the good habits and continue monitoring your wellbeing."

@app.route('/api/submit', methods=['POST'])
def submit_responses():
    """Submit questionnaire responses and get AI analysis"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        questions = data.get('questions', [])
        responses = data.get('responses', [])
        response_time = data.get('response_time_seconds', 0)

        if not questions or not responses:
            return jsonify({'error': 'Questions and responses are required'}), 400

        # Analyze responses
        analysis = analyze_responses(questions, responses)

        # Save to database
        daily_response = DailyResponse(
            user_id=user_id,
            questions=json.dumps(questions),
            responses=json.dumps(responses),
            burnout_score=analysis['score'],
            ai_analysis=json.dumps(analysis),
            concerns=json.dumps(analysis['concerns']),
            recommendations=json.dumps(analysis['recommendations']),
            urgency_level=analysis['urgency'],
            response_time_seconds=response_time
        )

        db.session.add(daily_response)
        db.session.commit()

        logger.info(f"Response submitted for user {user_id[:8]}... Score: {analysis['score']}")

        return jsonify({
            'success': True,
            'analysis': analysis,
            'message': 'Response submitted successfully'
        })

    except Exception as e:
        logger.error(f"Response submission error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to submit response'}), 500

# ==================== API ROUTES ====================

@app.route('/api/user-data')
def get_user_data():
    """Get user's historical data for dashboard (with demo data)"""
    try:
        user_id = session.get('user_id')

        # For testing without a real user session, return demo data
        if not user_id:
            # Generate demo chart data for last 30 days
            chart_data = []
            for i in range(30, 0, -1):
                date = datetime.utcnow() - timedelta(days=i)
                base_score = 70
                daily_variation = random.uniform(-8, 8)
                weekly_trend = -2 if i > 20 else 1  # Improvement trend
                score = base_score + daily_variation + weekly_trend
                score = max(30, min(95, score))  # Keep in reasonable range

                urgency = 'low'
                if score < 50:
                    urgency = 'high'
                elif score < 65:
                    urgency = 'medium'

                chart_data.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'score': round(score, 1),
                    'urgency': urgency
                })

            demo_analysis = {
                'score': 73,
                'concerns': ['Occasional heavy workload', 'Minor work-life balance issues'],
                'recommendations': [
                    {'type': 'immediate', 'action': 'Take a 10-minute mindfulness break'},
                    {'type': 'module', 'title': 'Time management strategies'},
                    {'type': 'preventive', 'habit': 'Daily 5-minute check-ins with yourself'}
                ],
                'urgency': 'low',
                'summary': 'Overall wellness is good with room for minor improvements'
            }

            return jsonify({
                'chart_data': chart_data,
                'latest_analysis': demo_analysis,
                'total_responses': 23,
                'avg_score': 72.8,
                'streak': 7,
                'progress_data': {
                    'energy': 7.3,
                    'satisfaction': 6.9,
                    'balance': 6.2,
                    'stress': 6.8
                }
            })

        # Get last 30 days of responses for real user
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        responses = DailyResponse.query.filter_by(user_id=user_id) \
            .filter(DailyResponse.created_at >= thirty_days_ago) \
            .order_by(DailyResponse.created_at.asc()).all()

        # Prepare chart data
        chart_data = []
        latest_analysis = None

        for response in responses:
            chart_data.append({
                'date': response.created_at.strftime('%Y-%m-%d'),
                'score': response.burnout_score or 0,
                'urgency': response.urgency_level or 'low'
            })

            if response == responses[-1]:  # Latest response
                try:
                    latest_analysis = json.loads(response.ai_analysis) if response.ai_analysis else {}
                except:
                    latest_analysis = {}

        return jsonify({
            'chart_data': chart_data,
            'latest_analysis': latest_analysis,
            'total_responses': len(responses),
            'avg_score': sum(r.burnout_score or 0 for r in responses) / len(responses) if responses else 0,
            'streak': calculate_check_in_streak(user_id)
        })

    except Exception as e:
        logger.error(f"User data retrieval error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve user data'}), 500

@app.route('/api/user-progress')
def get_user_progress():
    """Get detailed user progress analytics"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            # Return demo progress data
            return jsonify({
                'progress_data': {
                    'energy': random.uniform(6.5, 8.0),
                    'satisfaction': random.uniform(6.0, 7.5),
                    'balance': random.uniform(5.5, 7.0),
                    'stress': random.uniform(6.0, 7.5)
                },
                'trend_analysis': 'Gradual improvement over the past weeks',
                'streak': random.randint(3, 14)
            })

        # Get responses from last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        responses = DailyResponse.query.filter_by(user_id=user_id) \
            .filter(DailyResponse.created_at >= thirty_days_ago) \
            .order_by(DailyResponse.created_at.asc()).all()

        if not responses:
            return jsonify({
                'progress_data': {},
                'trend_analysis': 'No data available yet',
                'streak': 0
            })

        # Calculate progress metrics
        progress_data = calculate_progress_metrics(responses)

        # Calculate streak
        streak = calculate_check_in_streak(user_id)

        # Trend analysis
        trend_analysis = analyze_wellness_trend(responses)

        return jsonify({
            'progress_data': progress_data,
            'trend_analysis': trend_analysis,
            'streak': streak
        })

    except Exception as e:
        logger.error(f"User progress error: {str(e)}")
        return jsonify({'error': 'Failed to load progress data'}), 500

@app.route('/api/company-analytics')
def get_company_analytics():
    """Get company-wide analytics (demo data for now)"""
    try:
        period = request.args.get('period', '7d')

        # Generate realistic demo data
        demo_data = {
            'total_users': 147,
            'avg_wellness_score': 68.7,
            'high_risk_count': 12,
            'medium_risk_count': 28,
            'low_risk_count': 107,
            'participation_rate': 0.84,
            'department_breakdown': [
                {'department': 'Engineering', 'avg_score': 65.2, 'total': 45, 'high_risk': 8, 'medium_risk': 15},
                {'department': 'Sales', 'avg_score': 58.1, 'total': 35, 'high_risk': 12, 'medium_risk': 18},
                {'department': 'Marketing', 'avg_score': 72.3, 'total': 28, 'high_risk': 3, 'medium_risk': 8},
                {'department': 'HR', 'avg_score': 78.9, 'total': 15, 'high_risk': 1, 'medium_risk': 4},
                {'department': 'Finance', 'avg_score': 69.4, 'total': 24, 'high_risk': 2, 'medium_risk': 6}
            ],
            'trend_data': [
                {'date': '2025-07-20', 'avg_score': 67.2},
                {'date': '2025-07-21', 'avg_score': 68.1},
                {'date': '2025-07-22', 'avg_score': 69.3},
                {'date': '2025-07-23', 'avg_score': 68.7},
                {'date': '2025-07-24', 'avg_score': 70.1},
                {'date': '2025-07-25', 'avg_score': 69.8},
                {'date': '2025-07-26', 'avg_score': 68.9},
                {'date': '2025-07-27', 'avg_score': 68.7}
            ],
            'top_concerns': [
                {'name': 'Heavy Workload', 'count': 89, 'percentage': 60.5},
                {'name': 'Work-Life Balance', 'count': 67, 'percentage': 45.6},
                {'name': 'Lack of Recognition', 'count': 45, 'percentage': 30.6},
                {'name': 'Communication Issues', 'count': 38, 'percentage': 25.9},
                {'name': 'Limited Growth Opportunities', 'count': 29, 'percentage': 19.7}
            ]
        }

        return jsonify(demo_data)

    except Exception as e:
        logger.error(f"Company analytics error: {str(e)}")
        return jsonify({'error': 'Failed to load company analytics'}), 500

@app.route('/api/emergency-help', methods=['POST'])
def track_emergency_help():
    """Track emergency help usage (anonymous analytics)"""
    try:
        data = request.get_json()
        action = data.get('action', '')

        # Log emergency help usage for analytics (anonymized)
        logger.info(f"Emergency help action: {action}")

        # In a real app, you might store this in a separate analytics table
        # For now, just return success

        return jsonify({'success': True, 'message': f'Emergency action logged: {action}'})

    except Exception as e:
        logger.error(f"Emergency help tracking error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-data')
def export_user_data():
    """Export user's wellness data in various formats"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        format_type = request.args.get('format', 'json').lower()

        # Get user's data
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get all responses
        responses = DailyResponse.query.filter_by(user_id=user_id) \
            .order_by(DailyResponse.created_at.desc()).all()

        if format_type == 'csv':
            return export_csv(responses)
        elif format_type == 'pdf':
            return export_pdf(responses, user)
        else:  # json
            return export_json(responses, user)

    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({'error': 'Export failed'}), 500

# ==================== HELPER FUNCTIONS ====================

def export_csv(responses):
    """Export data as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        'Date', 'Wellness Score', 'Urgency Level', 'Concerns', 'Recommendations'
    ])

    # Data rows
    for response in responses:
        try:
            concerns = json.loads(response.concerns) if response.concerns else []
            recommendations = json.loads(response.recommendations) if response.recommendations else []

            writer.writerow([
                response.created_at.strftime('%Y-%m-%d %H:%M'),
                response.burnout_score or 0,
                response.urgency_level or 'low',
                '; '.join(concerns),
                '; '.join([r.get('action', str(r)) for r in recommendations if isinstance(r, dict)])
            ])
        except Exception as e:
            logger.warning(f"CSV export row error: {e}")
            continue

    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bloom-wellness-data.csv'}
    )

def export_json(responses, user):
    """Export data as JSON"""
    data = {
        'user_info': {
            'id': user.id,
            'department': user.department,
            'role_level': user.role_level,
            'created_at': user.created_at.isoformat(),
            'total_responses': len(responses)
        },
        'wellness_data': []
    }

    for response in responses:
        data['wellness_data'].append({
            'date': response.created_at.isoformat(),
            'wellness_score': response.burnout_score,
            'urgency_level': response.urgency_level,
            'concerns': json.loads(response.concerns) if response.concerns else [],
            'recommendations': json.loads(response.recommendations) if response.recommendations else [],
            'summary': json.loads(response.ai_analysis).get('summary', '') if response.ai_analysis else ''
        })

    return jsonify(data)

def export_pdf(responses, user):
    """Export data as PDF report"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph("🌸 Bloom Wellness Report", styles['Heading1']))
        story.append(Spacer(1, 20))

        # User info
        story.append(Paragraph(f"Department: {user.department or 'Not specified'}", styles['Normal']))
        story.append(Paragraph(f"Member Since: {user.created_at.strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Paragraph(f"Total Check-ins: {len(responses)}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Recent responses
        if responses:
            story.append(Paragraph("Recent Check-ins", styles['Heading2']))
            for response in responses[:10]:
                date_str = response.created_at.strftime('%B %d, %Y')
                score = response.burnout_score or 0
                story.append(Paragraph(f"{date_str} - Wellness Score: {score}/100", styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=bloom-wellness-report.pdf'}
        )

    except ImportError:
        logger.warning("reportlab not installed")
        return jsonify({'error': 'PDF export requires reportlab package'}), 501
    except Exception as e:
        logger.error(f"PDF export error: {str(e)}")
        return jsonify({'error': 'PDF generation failed'}), 500

def calculate_progress_metrics(responses):
    """Calculate detailed progress metrics from responses"""
    if not responses:
        return {}

    # Mock category breakdown (in real app, you'd categorize questions)
    random.seed(len(responses))  # Consistent "random" data based on response count

    return {
        'energy': random.uniform(5.0, 8.5),
        'satisfaction': random.uniform(5.5, 8.0),
        'balance': random.uniform(4.5, 7.5),
        'stress': random.uniform(5.0, 8.0)
    }

def calculate_check_in_streak(user_id):
    """Calculate current check-in streak"""
    try:
        # Get all responses ordered by date descending
        responses = DailyResponse.query.filter_by(user_id=user_id) \
            .order_by(DailyResponse.created_at.desc()).all()

        if not responses:
            return 0

        # Convert to dates only
        response_dates = list(set(r.created_at.date() for r in responses))
        response_dates.sort(reverse=True)

        # Calculate streak
        streak = 0
        current_date = datetime.utcnow().date()

        for response_date in response_dates:
            if response_date == current_date or response_date == current_date - timedelta(days=streak):
                streak += 1
                current_date = response_date
            else:
                break

        return streak

    except Exception as e:
        logger.error(f"Streak calculation error: {str(e)}")
        return 0

def analyze_wellness_trend(responses):
    """Analyze wellness trend over time"""
    if len(responses) < 2:
        return "Not enough data for trend analysis"

    # Get scores from first and second half of responses
    mid_point = len(responses) // 2
    first_half_avg = sum(r.burnout_score or 0 for r in responses[:mid_point]) / mid_point
    second_half_avg = sum(r.burnout_score or 0 for r in responses[mid_point:]) / (len(responses) - mid_point)

    # Note: Lower burnout score = better wellness
    if second_half_avg < first_half_avg - 5:
        return "Significant improvement in wellness"
    elif second_half_avg < first_half_avg:
        return "Gradual improvement in wellness"
    elif second_half_avg > first_half_avg + 5:
        return "Wellness requires attention"
    else:
        return "Stable wellness levels"

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'available_endpoints': [
            '/',
            '/health',
            '/register',
            '/api/user-data',
            '/api/user-progress',
            '/api/company-analytics',
            '/api/emergency-help',
            '/api/export-data'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.now().isoformat()
    }), 500

# ==================== INITIALIZATION ====================

def create_tables():
    """Create database tables"""
    with app.app_context():
        try:
            db.create_all()
            print("🌸 Bloom database initialized successfully!")

            # Test database connection
            user_count = User.query.count()
            response_count = DailyResponse.query.count()
            print(f"📊 Current users: {user_count}, Responses: {response_count}")

            # Create sample data if empty
            if user_count == 0:
                print("🌱 Creating sample data...")
                sample_user = User(
                    company_id='demo-company',
                    department='engineering',
                    role_level='senior'
                )
                db.session.add(sample_user)
                db.session.commit()
                print(f"✅ Sample user created: {sample_user.id[:8]}...")

        except Exception as e:
            print(f"❌ Database initialization failed: {e}")

if __name__ == '__main__':
    print("🚀 Starting Bloom server...")
    print("🌸 AI-powered burnout prevention platform")
    print("=" * 50)

    # Initialize database
    create_tables()

    print("🌐 Server will be available at:")
    print("   • http://localhost:5000")
    print("   • http://127.0.0.1:5000")
    print("\n📋 Available endpoints:")
    print("   • /health - System health check")
    print("   • /api/user-data - Demo dashboard data")
    print("   • /api/company-analytics - Company insights")
    print("   • /api/emergency-help - Emergency features")
    print("\n🛑 Press Ctrl+C to stop the server")
    print("=" * 50)

    # Start Flask app
    app.run(debug=True, port=5000, host='0.0.0.0')