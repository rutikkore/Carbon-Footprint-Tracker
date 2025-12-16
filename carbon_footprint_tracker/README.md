# 🌱 Carbon Footprint Tracker

A comprehensive web application to help users calculate, track, and reduce their daily carbon emissions through gamification and data visualization.

## 🎯 Features

- **User Authentication**: Secure registration and login system
- **Carbon Calculator**: Log daily activities across 4 categories (Transportation, Food, Energy, Waste)
- **Interactive Dashboard**: Real-time charts showing emissions by category and weekly trends
- **Gamification**: Earn badges and climb the leaderboard based on emission reduction
- **Profile Management**: Track personal progress and view activity history
- **Responsive Design**: Beautiful, mobile-friendly interface using Bootstrap

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. **Clone or download the project**
   ```bash
   cd carbon_footprint_tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:5000`

## 📊 How It Works

### 1. Register & Login
- Create your account with name, email, and password
- Secure authentication with hashed passwords

### 2. Log Daily Activities
- **Transportation**: Car, bus, train, flight, motorcycle, bicycle, walking
- **Food**: Meat, dairy, vegetarian, vegan, packaged food, local produce
- **Energy**: Electricity and natural gas usage
- **Waste**: Landfill waste, recycling, and composting

### 3. View Your Impact
- Interactive pie chart showing emissions by category
- Weekly trend line chart
- Real-time dashboard updates

### 4. Earn Rewards
- **Bronze Badge**: 10% emission reduction
- **Silver Badge**: 30% emission reduction  
- **Gold Badge**: 50% emission reduction
- Green Score calculation: `1000 - (Total CO₂ × 10)`

### 5. Compete & Improve
- Leaderboard ranking by Green Score
- Personal progress tracking
- Daily eco-friendly tips

## 🏗️ Project Structure

```
carbon_footprint_tracker/
│
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
│
├── templates/            # HTML templates
│   ├── base.html        # Base template with navigation
│   ├── index.html       # Landing page
│   ├── login.html       # Login page
│   ├── register.html    # Registration page
│   ├── dashboard.html   # User dashboard with charts
│   ├── calculator.html  # Carbon footprint calculator
│   ├── profile.html     # User profile and history
│   └── leaderboard.html # Leaderboard rankings
│
├── utils/
│   └── emission_factors.json  # CO₂ conversion factors
│
└── database/
    └── carbon_tracker.db     # SQLite database (auto-created)
```

## 🔧 Configuration

### Environment Variables
Set these environment variables for production:

```bash
export SECRET_KEY="your-secret-key-here"
export DATABASE_URL="sqlite:///database/carbon_tracker.db"
```

### Emission Factors
The application uses scientifically-backed CO₂ conversion factors stored in `utils/emission_factors.json`:

- **Transportation**: Car (0.24 kg/km), Bus (0.08 kg/km), Train (0.04 kg/km)
- **Food**: Meat (5.0 kg/serving), Dairy (2.5 kg/serving), Vegetarian (1.2 kg/serving)
- **Energy**: Electricity (0.92 kg/kWh), Gas (2.3 kg/kg)
- **Waste**: Landfill (1.5 kg/kg), Recycling (0.2 kg/kg)

## 📱 Usage Examples

### Calculate Your Daily Footprint
1. Go to Calculator page
2. Select transportation mode and distance
3. Choose food types and servings
4. Enter energy usage (electricity/gas)
5. Log waste disposal methods
6. Click "Calculate My Carbon Footprint"

### Track Your Progress
- Dashboard shows real-time charts and statistics
- Profile page displays activity history and earned badges
- Leaderboard compares your performance with other users

## 🛠️ Technical Details

### Backend
- **Framework**: Flask (Python)
- **Database**: SQLite with SQLAlchemy
- **Authentication**: Flask-Login with Werkzeug password hashing
- **Session Management**: Secure session handling

### Frontend
- **Styling**: Bootstrap 5 for responsive design
- **Charts**: Chart.js for interactive data visualization
- **Icons**: Font Awesome for consistent iconography
- **JavaScript**: Vanilla JS for form validation and UX enhancements

### Database Schema
- **users**: User accounts and authentication
- **emissions**: Daily activity logs and CO₂ calculations
- **badges**: Achievement tracking and gamification

## 🌍 Environmental Impact

This application helps users:
- **Understand** their personal carbon footprint
- **Visualize** emission patterns through interactive charts
- **Reduce** environmental impact through actionable insights
- **Compete** in friendly sustainability challenges
- **Learn** about eco-friendly alternatives

## 🔒 Security Features

- Password hashing using Werkzeug
- Session-based authentication
- CSRF protection ready
- SQL injection prevention through parameterized queries
- Secure cookie handling

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
The application is ready for deployment on:
- **Heroku**: Include Procfile
- **PythonAnywhere**: WSGI-compatible
- **Render**: Direct Flask deployment
- **Docker**: Containerization ready

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

If you encounter any issues:
1. Check the console for error messages
2. Ensure all dependencies are installed
3. Verify Python version compatibility
4. Check file permissions for database creation

## 🎉 Acknowledgments

- CO₂ emission factors based on EPA and IPCC guidelines
- Bootstrap for responsive design framework
- Chart.js for beautiful data visualizations
- Font Awesome for comprehensive icon library

---

**Start your journey toward a sustainable future today! 🌱**
