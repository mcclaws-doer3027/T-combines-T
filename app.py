from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import csv
import io

from config import Config
from reddit_oauth_analyzer import RedditOAuthAnalyzer

# Initialize
app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize analyzer
analyzer = RedditOAuthAnalyzer(
    app.config,
    reddit_username=app.config['REDDIT_USERNAME'],
    reddit_password=app.config['REDDIT_PASSWORD']
)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyses_used = db.Column(db.Integer, default=0)
    is_pro = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_analyze(self):
        return self.is_pro or self.analyses_used < Config.FREE_TIER_LIMIT

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    results = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    num_opportunities = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Account created!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    analyses = Analysis.query.filter_by(user_id=current_user.id)\
        .order_by(Analysis.created_at.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         user=current_user,
                         analyses=analyses,
                         free_limit=Config.FREE_TIER_LIMIT)

@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    if not current_user.can_analyze():
        flash('Free tier limit reached!', 'error')
        return redirect(url_for('dashboard'))
    
    category = request.form.get('category')
    
    try:
        results = analyzer.analyze_category(category, limit=20)
        
        analysis = Analysis(
            user_id=current_user.id,
            category=category,
            results=json.dumps(results),
            num_opportunities=len(results)
        )
        db.session.add(analysis)
        
        current_user.analyses_used += 1
        db.session.commit()
        
        return redirect(url_for('results', analysis_id=analysis.id))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/results/<int:analysis_id>')
@login_required
def results(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    results_data = json.loads(analysis.results)
    
    return render_template('results.html',
                         analysis=analysis,
                         results=results_data[:15])

@app.route('/export/<int:analysis_id>')
@login_required
def export_csv(analysis_id):
    analysis = Analysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != current_user.id:
        return "Access denied", 403
    
    results_data = json.loads(analysis.results)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Rank', 'Score', 'Title', 'Pain', 'WTP', 'People', 'Recommendation', 'URL'])
    
    for i, r in enumerate(results_data, 1):
        writer.writerow([
            i,
            r['analysis']['opportunity_score'],
            r['title'],
            r['analysis']['pain_score'],
            r['analysis']['willingness_to_pay'],
            r['analysis']['people_affected'],
            r['analysis']['recommendation'],
            r['url']
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'analysis_{analysis_id}.csv'
    )

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)