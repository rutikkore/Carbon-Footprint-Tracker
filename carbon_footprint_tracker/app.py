from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import json
import os
from functools import wraps
from urllib.parse import urlparse, urljoin
def parse_created_at(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    # Try common SQLite timestamp formats
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            pass
    # Try ISO
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None

def parse_float(value):
    try:
        if value is None:
            return 0.0
        value_str = str(value).strip()
        if value_str == '':
            return 0.0
        return float(value_str)
    except Exception:
        return 0.0

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['DATABASE'] = 'database/carbon_tracker.db'

# Resolve important paths relative to this file so CWD doesn't matter
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMISSION_FACTORS_PATH = os.path.join(BASE_DIR, 'utils', 'emission_factors.json')

# Tree offset assumptions
# Average mature tree sequesters about 21 kg CO₂ per year (conservative).
# We will present number of trees to offset total emissions over one year.
TREE_CO2_SEQUESTRATION_KG_PER_YEAR = float(os.environ.get('TREE_CO2_KG_PER_YEAR', 21))

def estimate_trees_needed(total_emissions_kg: float) -> int:
    """Estimate number of trees needed to offset given CO₂ (kg) annually.

    Uses TREE_CO2_SEQUESTRATION_KG_PER_YEAR as sequestration per tree per year.
    Returns ceiling to the next whole tree.
    """
    try:
        emissions = max(0.0, float(total_emissions_kg))
    except Exception:
        emissions = 0.0
    if TREE_CO2_SEQUESTRATION_KG_PER_YEAR <= 0:
        return 0
    # Round up to whole tree count
    import math
    return int(math.ceil(emissions / TREE_CO2_SEQUESTRATION_KG_PER_YEAR))

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, name, email, password_hash, created_at):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        created_at = parse_created_at(user['created_at'])
        return User(user['id'], user['name'], user['email'], user['password_hash'], created_at)
    return None

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create emissions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS emissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            activity TEXT NOT NULL,
            emission_value REAL NOT NULL,
            date DATE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create badges table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_name TEXT NOT NULL,
            date_earned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if not name or not email or not password:
            flash('All fields are required!', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        
        # Check if user already exists
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('Email already registered!', 'error')
            conn.close()
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                    (name, email, password_hash))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        next_page = request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['name'], user['email'], user['password_hash'], parse_created_at(user['created_at']))
            login_user(user_obj)
            flash(f'Welcome, {user["name"]}!', 'success')
            # Prefer next from form (POST), fallback to query string
            next_page = (request.form.get('next') or request.args.get('next') or '').strip()
            # Ignore accidental 'None' or '/None' values rendered from templates
            if next_page in ('', 'None', '/None'):
                next_page = ''
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Get user's total emissions
    total_emissions = conn.execute('''
        SELECT COALESCE(SUM(emission_value), 0) as total 
        FROM emissions WHERE user_id = ?
    ''', (current_user.id,)).fetchone()['total']
    
    # Get emissions by category for pie chart
    category_rows = conn.execute('''
        SELECT category, SUM(emission_value) as total
        FROM emissions 
        WHERE user_id = ? 
        GROUP BY category
    ''', (current_user.id,)).fetchall()
    category_emissions = [
        { 'category': row['category'], 'total': float(row['total'] or 0) }
        for row in category_rows
    ]
    
    # Get weekly trend data
    weekly_rows = conn.execute('''
        SELECT DATE(date) as emission_date, SUM(emission_value) as daily_total
        FROM emissions 
        WHERE user_id = ? AND date >= date('now', '-7 days')
        GROUP BY DATE(date)
        ORDER BY date
    ''', (current_user.id,)).fetchall()
    weekly_data = [
        { 'emission_date': row['emission_date'], 'daily_total': float(row['daily_total'] or 0) }
        for row in weekly_rows
    ]
    
    # Get user's badges
    badges_rows = conn.execute('''
        SELECT badge_name, date_earned 
        FROM badges 
        WHERE user_id = ?
        ORDER BY date_earned DESC
    ''', (current_user.id,)).fetchall()
    
    # Convert date strings to datetime objects for badges
    badges = []
    for row in badges_rows:
        row_dict = dict(row)
        if row_dict['date_earned']:
            # Parse the datetime string to datetime object
            if isinstance(row_dict['date_earned'], str):
                row_dict['date_earned'] = datetime.strptime(row_dict['date_earned'], '%Y-%m-%d %H:%M:%S')
        badges.append(row_dict)
    
    conn.close()
    
    # Calculate green score (lower emissions = higher score)
    green_score = max(0, 1000 - int(total_emissions * 10))
    
    # Random eco tips
    eco_tips = [
        "Use public transport to reduce your carbon footprint!",
        "Try eating more plant-based meals this week.",
        "Unplug electronics when not in use to save energy.",
        "Consider carpooling or biking for short trips.",
        "Reduce, reuse, and recycle to minimize waste."
    ]
    
    import random
    daily_tip = random.choice(eco_tips)
    
    trees_needed = estimate_trees_needed(total_emissions)
    return render_template('dashboard.html', 
                         total_emissions=round(total_emissions, 2),
                         green_score=green_score,
                         category_emissions=category_emissions,
                         weekly_data=weekly_data,
                         badges=badges,
                         daily_tip=daily_tip,
                         trees_needed=trees_needed,
                         tree_absorption=TREE_CO2_SEQUESTRATION_KG_PER_YEAR)

@app.route('/calculator', methods=['GET', 'POST'])
@login_required
def calculator():
    if request.method == 'POST':
        # Load emission factors
        with open(EMISSION_FACTORS_PATH, 'r') as f:
            factors = json.load(f)
        
        total_emissions = 0
        activities_logged = []
        
        conn = get_db_connection()
        
        # Transportation
        if request.form.get('transport_mode'):
            mode = request.form['transport_mode']
            distance = parse_float(request.form.get('transport_distance'))
            if distance > 0:
                emission = distance * factors['transportation'][mode]
                total_emissions += emission
                
                conn.execute('''
                    INSERT INTO emissions (user_id, category, activity, emission_value, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (current_user.id, 'Transportation', f'{mode} - {distance}km', emission, datetime.now().date()))
                activities_logged.append(f'{mode}: {distance}km = {emission:.2f} kg CO₂')
        
        # Food
        if request.form.get('food_type'):
            food_type = request.form['food_type']
            servings = parse_float(request.form.get('food_servings'))
            if servings > 0:
                emission = servings * factors['food'][food_type]
                total_emissions += emission
                
                conn.execute('''
                    INSERT INTO emissions (user_id, category, activity, emission_value, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (current_user.id, 'Food', f'{food_type} - {servings} servings', emission, datetime.now().date()))
                activities_logged.append(f'{food_type}: {servings} servings = {emission:.2f} kg CO₂')
        
        # Energy
        electricity = parse_float(request.form.get('electricity'))
        if electricity > 0:
            emission = electricity * factors['energy']['electricity']
            total_emissions += emission
            
            conn.execute('''
                INSERT INTO emissions (user_id, category, activity, emission_value, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, 'Energy', f'Electricity - {electricity}kWh', emission, datetime.now().date()))
            activities_logged.append(f'Electricity: {electricity}kWh = {emission:.2f} kg CO₂')
        
        # Natural Gas
        gas = parse_float(request.form.get('gas'))
        if gas > 0:
            emission = gas * factors['energy']['gas']
            total_emissions += emission
            
            conn.execute('''
                INSERT INTO emissions (user_id, category, activity, emission_value, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, 'Energy', f'Natural Gas - {gas}kg', emission, datetime.now().date()))
            activities_logged.append(f'Natural Gas: {gas}kg = {emission:.2f} kg CO₂')
        
        # Waste
        landfill = parse_float(request.form.get('landfill'))
        if landfill > 0:
            emission = landfill * factors['waste']['landfill']
            total_emissions += emission
            
            conn.execute('''
                INSERT INTO emissions (user_id, category, activity, emission_value, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, 'Waste', f'Landfill - {landfill}kg', emission, datetime.now().date()))
            activities_logged.append(f'Landfill waste: {landfill}kg = {emission:.2f} kg CO₂')
        
        # Recycling (negative emission - reduces footprint)
        if request.form.get('recycling'):
            # Assume recycling 1kg of waste reduces emissions by 0.5kg CO₂
            emission_reduction = 1.0 * abs(factors['waste']['recycling'])
            total_emissions -= emission_reduction
            
            conn.execute('''
                INSERT INTO emissions (user_id, category, activity, emission_value, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, 'Waste', f'Recycling - 1kg', -emission_reduction, datetime.now().date()))
            activities_logged.append(f'Recycling: -1kg waste = -{emission_reduction:.2f} kg CO₂')
        
        # Composting (negative emission - reduces footprint)
        if request.form.get('composting'):
            # Assume composting 1kg of organic waste reduces emissions by 0.3kg CO₂
            emission_reduction = 1.0 * abs(factors['waste']['composting'])
            total_emissions -= emission_reduction
            
            conn.execute('''
                INSERT INTO emissions (user_id, category, activity, emission_value, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, 'Waste', f'Composting - 1kg', -emission_reduction, datetime.now().date()))
            activities_logged.append(f'Composting: -1kg organic waste = -{emission_reduction:.2f} kg CO₂')
        
        conn.commit()
        
        # Check for badge eligibility
        check_and_award_badges(current_user.id, total_emissions)
        
        conn.close()
        
        flash(f'You emitted {total_emissions:.2f} kg CO₂ today.', 'info')
        trees_needed = estimate_trees_needed(total_emissions)
        return render_template('calculator.html', 
                             calculation_result=total_emissions,
                             activities=activities_logged,
                             trees_needed=trees_needed,
                             tree_absorption=TREE_CO2_SEQUESTRATION_KG_PER_YEAR)
    
    return render_template('calculator.html')

def check_and_award_badges(user_id, daily_emissions):
    """Check if user deserves a badge based on their emissions"""
    conn = get_db_connection()
    
    # Get user's average daily emissions
    avg_emissions = conn.execute('''
        SELECT AVG(daily_total) as avg_daily
        FROM (
            SELECT DATE(date) as emission_date, SUM(emission_value) as daily_total
            FROM emissions 
            WHERE user_id = ?
            GROUP BY DATE(date)
        )
    ''', (user_id,)).fetchone()['avg_daily']
    
    if avg_emissions is None:
        conn.close()
        return
    
    # Award badges based on performance
    badges_to_award = []
    
    if daily_emissions < avg_emissions * 0.5:  # 50% reduction
        badges_to_award.append('Gold Eco Warrior')
    elif daily_emissions < avg_emissions * 0.7:  # 30% reduction
        badges_to_award.append('Silver Green Champion')
    elif daily_emissions < avg_emissions * 0.9:  # 10% reduction
        badges_to_award.append('Bronze Earth Friend')
    
    # Check if user already has these badges today
    for badge in badges_to_award:
        existing = conn.execute('''
            SELECT id FROM badges 
            WHERE user_id = ? AND badge_name = ? AND DATE(date_earned) = DATE('now')
        ''', (user_id, badge)).fetchone()
        
        if not existing:
            conn.execute('''
                INSERT INTO badges (user_id, badge_name) VALUES (?, ?)
            ''', (user_id, badge))
            flash(f'🎉 Congratulations! You earned the {badge} badge!', 'success')
    
    conn.commit()
    conn.close()

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle profile update
        name = request.form['name']
        new_password = request.form.get('new_password')
        
        if not name:
            flash('Name is required!', 'error')
            return redirect(url_for('profile'))
        
        conn = get_db_connection()
        
        # Update name
        conn.execute('UPDATE users SET name = ? WHERE id = ?', (name, current_user.id))
        
        # Update password if provided
        if new_password and len(new_password) >= 6:
            password_hash = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, current_user.id))
        
        conn.commit()
        conn.close()
        
        # Update current user object
        current_user.name = name
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    # GET request - display profile
    conn = get_db_connection()
    
    # Get user's emission history
    history_rows = conn.execute('''
        SELECT category, activity, emission_value, date
        FROM emissions 
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT 20
    ''', (current_user.id,)).fetchall()
    
    # Convert date strings to datetime objects for history
    history = []
    for row in history_rows:
        row_dict = {
            'category': row['category'],
            'activity': row['activity'],
            'emission_value': float(row['emission_value'] or 0),
            'date': None
        }
        if row['date']:
            try:
                row_dict['date'] = datetime.strptime(row['date'], '%Y-%m-%d')
            except Exception:
                try:
                    row_dict['date'] = datetime.fromisoformat(str(row['date']))
                except Exception:
                    row_dict['date'] = datetime.now()
        history.append(row_dict)
    
    # Get user's badges
    badges_rows = conn.execute('''
        SELECT badge_name, date_earned 
        FROM badges 
        WHERE user_id = ?
        ORDER BY date_earned DESC
    ''', (current_user.id,)).fetchall()
    
    # Convert date strings to datetime objects for badges
    badges = []
    for row in badges_rows:
        badge_dict = {
            'badge_name': row['badge_name'],
            'date_earned': None
        }
        if row['date_earned']:
            try:
                badge_dict['date_earned'] = datetime.strptime(row['date_earned'], '%Y-%m-%d %H:%M:%S')
            except Exception:
                try:
                    badge_dict['date_earned'] = datetime.fromisoformat(str(row['date_earned']))
                except Exception:
                    badge_dict['date_earned'] = datetime.now()
        badges.append(badge_dict)
    
    # Get total emissions
    total_emissions = conn.execute('''
        SELECT COALESCE(SUM(emission_value), 0) as total 
        FROM emissions WHERE user_id = ?
    ''', (current_user.id,)).fetchone()['total']
    
    conn.close()
    
    green_score = max(0, 1000 - int(total_emissions * 10))
    
    trees_needed = estimate_trees_needed(total_emissions)
    return render_template('profile.html', 
                         history=history,
                         badges=badges,
                         total_emissions=round(total_emissions, 2),
                         green_score=green_score,
                         trees_needed=trees_needed,
                         tree_absorption=TREE_CO2_SEQUESTRATION_KG_PER_YEAR)

@app.route('/leaderboard')
@login_required
def leaderboard():
    conn = get_db_connection()
    
    # Get top users by green score (calculated as 1000 - total_emissions * 10)
    leaderboard_data = conn.execute('''
        SELECT u.name, 
               COALESCE(SUM(e.emission_value), 0) as total_emissions,
               MAX(1000 - COALESCE(SUM(e.emission_value), 0) * 10, 0) as green_score,
               COUNT(DISTINCT b.id) as badge_count
        FROM users u
        LEFT JOIN emissions e ON u.id = e.user_id
        LEFT JOIN badges b ON u.id = b.user_id
        GROUP BY u.id, u.name
        ORDER BY green_score DESC
        LIMIT 10
    ''').fetchall()
    
    conn.close()
    
    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Ensure database directory exists
    os.makedirs('database', exist_ok=True)
    os.makedirs('utils', exist_ok=True)
    
    # Initialize database
    init_db()
    
    app.run(debug=True)
