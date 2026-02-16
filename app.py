from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import csv
import io
from matching import rank_categories
from revenue_calculator import estimate_revenue
import json
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
    # In app.py, add new model:

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    background = db.Column(db.String(50))
    interests = db.Column(db.Text)  # JSON array as string
    time_available = db.Column(db.String(50))
    budget = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        # Redirect to onboarding for new users
        return redirect(url_for('onboarding'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Redirect to personalized dashboard
            return redirect(url_for('personalized_dashboard'))
        
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
        print(f"\n⏱️  Starting analysis for {current_user.email}...")
        
        results = analyzer.analyze_idea(category)
        
        analysis = Analysis(
            user_id=current_user.id,
            category=category,
            results=json.dumps(results),
            num_opportunities=len(results)
        )
        db.session.add(analysis)
        
        current_user.analyses_used += 1
        db.session.commit()
        return redirect(url_for('results_chart', analysis_id=analysis.id))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('personalized_dashboard'))


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
    
@app.route('/personalized_dashboard')
@login_required
def personalized_dashboard():
    """Show personalized dashboard with ranked categories"""
    
    profile_data = get_user_profile(current_user.id)  # ✅ DEFINE IT FIRST
    
    if not profile_data:
        return redirect(url_for('onboarding'))
    
    # Rank categories based on profile
    ranked_categories = rank_categories(profile_data)
    
    return render_template(
        'personalized_dashboard.html',
        profile=profile_data,
        ranked_categories=ranked_categories
    )

@app.route('/results_chart/<int:analysis_id>')
@login_required
def results_chart(analysis_id):
    """Show results as interactive chart"""
    
    analysis = Analysis.query.get_or_404(analysis_id)
    
    if analysis.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    results_data = json.loads(analysis.results)
    
    # Take top 15 for chart
    top_results = results_data[:15]
    
    return render_template('results_chart.html',
                         analysis=analysis,
                         results=top_results)

# Initialize database
with app.app_context():
    db.create_all()


    # In app.py:

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        # Check if user has completed onboarding
        profile_data = get_user_profile(current_user.id)
    
        if not profile:
            profile = UserProfile(user_id=current_user.id)
        
        profile.background = request.form.get('background')
        profile.interests = json.dumps(request.form.getlist('interests'))
        profile.time_available = request.form.get('time_available')
        profile.budget = request.form.get('budget')
        profile.updated_at = datetime.utcnow()
        
        db.session.add(profile)
        db.session.commit()
        
        return redirect(url_for('personalized_dashboard'))
    
    return render_template('onboarding.html')

# Rank categories based on profile
    ranked_categories = rank_categories(profile_data)
    
    return render_template('personalized_dashboard.html',
                         profile=profile_data,
                         ranked_categories=ranked_categories)
    
    # Take top 15 for chart
    top_results = results_data[:15]
    
    return render_template('results_chart.html',
                         analysis=analysis,
                         results=top_results)

@app.route('/problem/<string:problem_id>')
@login_required
def problem_detail(problem_id):
    """Show detailed view of a single problem"""
    
    # Find the analysis containing this problem
    # (In real app, you'd store problems separately)
    # For now, search through user's recent analyses
    
    analyses = Analysis.query.filter_by(user_id=current_user.id)\
        .order_by(Analysis.created_at.desc()).limit(10).all()
    
    problem = None
    analysis_id = None
    
    for analysis in analyses:
        results = json.loads(analysis.results)
        for result in results:
            if result['id'] == problem_id:
                problem = result
                analysis_id = analysis.id
                break
        if problem:
            break
    
    if not problem:
        flash('Problem not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Calculate revenue projections
    revenue = estimate_revenue(problem['analysis'])
    
    # Get competitors (if available)
    competitors = problem.get('competitors', {})
    
    return render_template('problem_detail.html',
                         problem=problem,
                         analysis_id=analysis_id,
                         revenue=revenue,
                         competitors=competitors)

# Helper function in app.py:

def get_user_profile(user_id):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        return {
            'background': profile.background,
            'interests': json.loads(profile.interests),
            'time_available': profile.time_available,
            'budget': profile.budget
        }
if __name__ == '__main__':
    app.run(debug=True, port=5000)
    