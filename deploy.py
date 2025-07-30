#!/usr/bin/env python3
"""
Bloom App Deployment Setup
Handles production deployment configuration and setup
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class BloomDeployer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.requirements_prod = [
            'flask>=2.3.0',
            'flask-sqlalchemy>=3.0.0',
            'openai>=1.0.0',
            'python-dotenv>=1.0.0',
            'gunicorn>=21.0.0',
            'psycopg2-binary>=2.9.0',
            'reportlab>=4.0.0',
            'openpyxl>=3.1.0'
        ]

    def create_production_files(self):
        """Create necessary production files"""
        print("📝 Creating production files...")

        # Procfile for Heroku
        procfile_content = "web: gunicorn app:app\n"
        with open(self.project_root / 'Procfile', 'w') as f:
            f.write(procfile_content)
        print("   ✅ Created Procfile")

        # Production requirements
        with open(self.project_root / 'requirements-prod.txt', 'w') as f:
            f.write('\n'.join(self.requirements_prod))
        print("   ✅ Created requirements-prod.txt")

        # Production environment template
        env_prod_content = """# Production Environment Variables
FLASK_ENV=production
FLASK_SECRET_KEY=your-production-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=postgresql://username:password@host:port/database

# Optional: Analytics and monitoring
SENTRY_DSN=your-sentry-dsn-for-error-tracking
GA_TRACKING_ID=your-google-analytics-id

# Email settings (for reports)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@company.com
MAIL_PASSWORD=your-app-password
"""
        with open(self.project_root / '.env.production', 'w') as f:
            f.write(env_prod_content)
        print("   ✅ Created .env.production template")

        # Docker configuration
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash bloom
RUN chown -R bloom:bloom /app
USER bloom

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:app"]
"""
        with open(self.project_root / 'Dockerfile', 'w') as f:
            f.write(dockerfile_content)
        print("   ✅ Created Dockerfile")

        # Docker Compose for local testing
        docker_compose_content = """version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://bloom:password@db:5432/bloom
      - FLASK_ENV=production
    depends_on:
      - db
    volumes:
      - ./.env.production:/app/.env

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: bloom
      POSTGRES_USER: bloom
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
"""
        with open(self.project_root / 'docker-compose.yml', 'w') as f:
            f.write(docker_compose_content)
        print("   ✅ Created docker-compose.yml")

        # GitHub Actions CI/CD
        github_dir = self.project_root / '.github' / 'workflows'
        github_dir.mkdir(parents=True, exist_ok=True)

        github_actions_content = """name: Deploy Bloom App

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      run: |
        python run_tests.py
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
        heroku_app_name: "your-bloom-app"
        heroku_email: "your-email@example.com"
"""
        with open(github_dir / 'deploy.yml', 'w') as f:
            f.write(github_actions_content)
        print("   ✅ Created GitHub Actions workflow")

    def create_startup_script(self):
        """Create startup script for easy deployment"""
        startup_content = """#!/bin/bash
# Bloom App Startup Script

set -e

echo "🌸 Starting Bloom App Deployment..."

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production file not found!"
    echo "Please copy .env.production template and fill in your values."
    exit 1
fi

# Load production environment
export $(cat .env.production | grep -v '^#' | xargs)

# Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY not set in .env.production"
    exit 1
fi

if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "❌ Error: FLASK_SECRET_KEY not set in .env.production"
    exit 1
fi

# Install production dependencies
echo "📦 Installing production dependencies..."
pip install -r requirements-prod.txt

# Run database migrations
echo "🗄️  Setting up database..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

# Run tests
echo "🧪 Running production tests..."
python run_tests.py

if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Please fix issues before deployment."
    exit 1
fi

# Start production server
echo "🚀 Starting production server..."
echo "Visit http://localhost:8000 to access your Bloom app"

# Use gunicorn for production
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 app:app
"""
        startup_script = self.project_root / 'start_production.sh'
        with open(startup_script, 'w') as f:
            f.write(startup_content)

        # Make executable
        os.chmod(startup_script, 0o755)
        print("   ✅ Created start_production.sh")

    def create_monitoring_setup(self):
        """Create monitoring and logging setup"""
        print("📊 Setting up monitoring...")

        # Health check endpoint
        health_check_content = """
# Add this to your app.py file

@app.route('/health')
def health_check():
    \"\"\"Health check endpoint for monitoring\"\"\"
    try:
        # Test database connection
        db.engine.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/metrics')
def metrics():
    \"\"\"Basic metrics endpoint\"\"\"
    try:
        total_users = User.query.count()
        total_responses = DailyResponse.query.count()
        recent_responses = DailyResponse.query.filter(
            DailyResponse.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return jsonify({
            'total_users': total_users,
            'total_responses': total_responses,
            'recent_responses_7d': recent_responses,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

        with open(self.project_root / 'monitoring_endpoints.py', 'w') as f:
            f.write(health_check_content)
        print("   ✅ Created monitoring endpoints")

        # Logging configuration
        logging_config_content = """
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    \"\"\"Configure application logging\"\"\"
    
    if not app.debug and not app.testing:
        # File logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/bloom.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Console logging
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Bloom application startup')

# Add to your app.py:
# from logging_config import setup_logging
# setup_logging(app)
"""

        with open(self.project_root / 'logging_config.py', 'w') as f:
            f.write(logging_config_content)
        print("   ✅ Created logging configuration")

    def create_backup_scripts(self):
        """Create backup and restore scripts"""
        print("💾 Creating backup scripts...")

        backup_script_content = """#!/bin/bash
# Bloom App Database Backup Script

set -e

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="bloom_backup_$DATE.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not set"
    exit 1
fi

echo "📦 Creating database backup..."

# Create backup
pg_dump $DATABASE_URL > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_DIR/$BACKUP_FILE.gz"

# Clean up old backups (keep last 30 days)
find $BACKUP_DIR -name "bloom_backup_*.sql.gz" -mtime +30 -delete

echo "🧹 Cleaned up old backups"
"""

        backup_script = self.project_root / 'backup_database.sh'
        with open(backup_script, 'w') as f:
            f.write(backup_script_content)
        os.chmod(backup_script, 0o755)
        print("   ✅ Created backup_database.sh")

    def generate_security_checklist(self):
        """Generate security checklist for production"""
        print("🔒 Generating security checklist...")

        security_checklist = """# Bloom App Security Checklist

## Before Production Deployment

### Environment & Configuration
- [ ] Set strong FLASK_SECRET_KEY (32+ random characters)
- [ ] Use environment variables for all secrets
- [ ] Set FLASK_ENV=production
- [ ] Enable HTTPS in production
- [ ] Configure proper CORS settings
- [ ] Set secure cookie settings

### Database Security
- [ ] Use strong database passwords
- [ ] Enable database connection encryption
- [ ] Restrict database access by IP
- [ ] Regular database backups
- [ ] Database user has minimal required permissions

### API Security
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (using SQLAlchemy ORM)
- [ ] XSS protection enabled
- [ ] CSRF protection for forms

### Data Privacy
- [ ] User data is properly anonymized
- [ ] No PII stored unnecessarily
- [ ] Data retention policies implemented
- [ ] GDPR compliance (if applicable)
- [ ] Clear privacy policy

### Infrastructure Security
- [ ] Server OS kept updated
- [ ] Firewall configured properly
- [ ] SSH keys instead of passwords
- [ ] Regular security updates
- [ ] Monitoring and alerting set up

### Application Security
- [ ] Dependencies regularly updated
- [ ] Security headers configured
- [ ] Error messages don't leak sensitive info
- [ ] Logging doesn't capture sensitive data
- [ ] Session management secure

### Monitoring & Compliance
- [ ] Security monitoring in place
- [ ] Audit logging enabled
- [ ] Incident response plan
- [ ] Regular security assessments
- [ ] Compliance documentation

## Post-Deployment Monitoring

### Daily Checks
- [ ] Application health status
- [ ] Error logs review
- [ ] Performance metrics
- [ ] User activity patterns

### Weekly Checks
- [ ] Security log review
- [ ] Dependency vulnerability scans
- [ ] Backup verification
- [ ] Performance optimization

### Monthly Checks
- [ ] Full security audit
- [ ] Access review
- [ ] Compliance verification
- [ ] Disaster recovery testing

## Emergency Procedures

### Data Breach Response
1. Immediately isolate affected systems
2. Assess scope of breach
3. Notify stakeholders within 24 hours
4. Document incident thoroughly
5. Implement corrective measures
6. Conduct post-incident review

### System Compromise
1. Take affected systems offline
2. Preserve evidence
3. Restore from clean backups
4. Update all credentials
5. Implement additional monitoring
6. Review and update security measures
"""

        with open(self.project_root / 'SECURITY_CHECKLIST.md', 'w') as f:
            f.write(security_checklist)
        print("   ✅ Created SECURITY_CHECKLIST.md")

    def deploy(self):
        """Run full deployment setup"""
        print("🌸 Bloom App Production Deployment Setup")
        print("=" * 50)

        try:
            self.create_production_files()
            self.create_startup_script()
            self.create_monitoring_setup()
            self.create_backup_scripts()
            self.generate_security_checklist()

            print("\n✅ Deployment setup complete!")
            print("\n📋 Next Steps:")
            print("1. Copy .env.production and fill in your production values")
            print("2. Review SECURITY_CHECKLIST.md and complete all items")
            print("3. Run: ./start_production.sh")
            print("4. Set up monitoring and backups")
            print("5. Configure domain and SSL certificate")

            print("\n🚀 Deployment Options:")
            print("• Local Production: ./start_production.sh")
            print("• Docker: docker-compose up")
            print("• Heroku: git push heroku main")
            print("• Manual Server: Follow Dockerfile instructions")

        except Exception as e:
            print(f"❌ Deployment setup failed: {e}")
            return False

        return True

if __name__ == "__main__":
    deployer = BloomDeployer()
    deployer.deploy()