import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Opportunity, User
from scraper import run_scraper_pipeline
from notifier import send_whatsapp_alerts
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')
# Default to SQLite if DATABASE_URL is not set
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ioas.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    from datetime import datetime
    now = datetime.utcnow()
    # Filter for future deadlines, but allow ones with no deadline
    opportunities = Opportunity.query.filter(
        db.or_(
            Opportunity.registration_deadline >= now,
            Opportunity.registration_deadline == None
        )
    ).order_by(Opportunity.created_at.desc()).all()
    users = User.query.all()
    
    hackathons = [o for o in opportunities if o.type == 'Hackathon']
    competitions = [o for o in opportunities if o.type == 'Competition']
    conferences = [o for o in opportunities if o.type == 'Conference']
    
    return render_template('index.html', 
                           hackathons=hackathons, 
                           competitions=competitions, 
                           conferences=conferences,
                           users=users)

@app.route('/run-scraper', methods=['POST'])
def run_scraper():
    count = run_scraper_pipeline()
    flash(f'Successfully ran aggregation pipeline! {count} opportunities collected or updated.', 'success')
    return redirect(url_for('index'))

@app.route('/send-alerts', methods=['POST'])
def send_alerts():
    alerts = send_whatsapp_alerts()
    flash(f'Successfully sent {len(alerts)} WhatsApp alerts!', 'success')
    return redirect(url_for('alerts_log'))

@app.route('/subscribe', methods=['POST'])
def subscribe():
    name = request.form.get('name')
    phone = request.form.get('phone')
    interests = request.form.get('interests')
    branch = request.form.get('branch')
    preferred_types = request.form.getlist('preferred_types')
    whatsapp_enabled = request.form.get('whatsapp_enabled') == 'on'
    
    if not name or not phone:
        flash('Name and Phone are required!', 'danger')
        return redirect(url_for('index'))
        
    user = User.query.filter_by(phone_number=phone).first()
    if user:
        user.name = name
        user.interests = interests
        user.branch = branch
        user.preferred_types = ','.join(preferred_types)
        user.whatsapp_enabled = whatsapp_enabled
        flash('Your preferences have been updated!', 'success')
    else:
        user = User(name=name, phone_number=phone, interests=interests, branch=branch,
                    preferred_types=','.join(preferred_types), whatsapp_enabled=whatsapp_enabled)
        db.session.add(user)
        flash('Successfully subscribed to alerts!', 'success')
        
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/chatbot', methods=['POST'])
def chatbot():
    """
    Endpoint for n8n/GreenAPI to send incoming WhatsApp messages to.
    Expects JSON: {"phone": "917219...", "text": "show me AI hackathons"}
    Returns JSON: {"reply": "..."}
    """
    data = request.json or {}
    user_phone = data.get('phone', '')
    user_message = data.get('text', '').lower()
    
    reply = "I didn't quite catch that. Try asking for 'hackathons', 'conferences', or 'subscribe [interests]'."
    
    if 'hackathon' in user_message or 'competition' in user_message:
        opps = Opportunity.query.filter(Opportunity.type.in_(['Hackathon', 'Competition'])).limit(3).all()
        if opps:
            reply = "🚀 *Upcoming Hackathons:*\n\n"
            for o in opps:
                reply += f"- *{o.title}*\n  Platform: {o.source_platform}\n  Link: {o.url}\n\n"
        else:
            reply = "I couldn't find any upcoming hackathons right now."
            
    elif 'conference' in user_message:
        opps = Opportunity.query.filter_by(type='Conference').limit(3).all()
        if opps:
            reply = "📚 *Upcoming Conferences:*\n\n"
            for o in opps:
                scopus = "✅" if o.is_scopus_indexed else "❌"
                reply += f"- *{o.title}*\n  Scopus: {scopus}\n  Link: {o.url}\n\n"
        else:
            reply = "I couldn't find any upcoming conferences right now."
            
    elif 'subscribe' in user_message:
        # Example: "subscribe AI, Web3"
        interests = user_message.replace('subscribe', '').strip()
        user = User.query.filter_by(phone_number=user_phone).first()
        if user:
            user.interests = interests
            reply = f"✅ Your interests have been updated to: {interests}"
        else:
            user = User(name="WhatsApp User", phone_number=user_phone, interests=interests)
            db.session.add(user)
            reply = f"✅ You are now subscribed with interests: {interests}"
        db.session.commit()

    return jsonify({"reply": reply})

@app.route('/alerts')
def alerts_log():
    import json
    log_data = []
    if os.path.exists('whatsapp_alerts_log.json'):
        try:
            with open('whatsapp_alerts_log.json', 'r') as f:
                log_data = json.load(f)
        except:
            pass
    # Get the latest batch of messages
    latest_messages = []
    if log_data:
        latest_messages = log_data[-1].get('messages', [])
        
    return render_template('alerts.html', messages=latest_messages)

def scheduled_pipeline():
    with app.app_context():
        print("Running scheduled aggregation pipeline...")
        run_scraper_pipeline()
        send_whatsapp_alerts()
        print("Scheduled pipeline completed.")

scheduler = BackgroundScheduler()
# Run every 6 hours
scheduler.add_job(func=scheduled_pipeline, trigger="interval", hours=6)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
