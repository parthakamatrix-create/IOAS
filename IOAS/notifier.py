import json
import os
from models import db, Opportunity, User, AlertHistory
from datetime import datetime

ALERTS_FILE = 'whatsapp_alerts_log.json'

def check_rules(deadline_name, deadline_date, now):
    if not deadline_date:
        return []
    
    delta = deadline_date - now
    days_left = delta.days
    hours_left = delta.seconds // 3600
    
    rules_met = []
    diff = (deadline_date - now).total_seconds() / 86400.0
    
    if 6.0 <= diff < 7.0:
        rules_met.append(f'{deadline_name}_7_days')
    elif 2.0 <= diff < 3.0:
        rules_met.append(f'{deadline_name}_3_days')
    elif 0.0 < diff <= 1.0:
        rules_met.append(f'{deadline_name}_24_hours')
    elif -1.0 < diff <= 0.0:
        rules_met.append(f'{deadline_name}_today')
        
    return rules_met

def matches_preferences(user, opp):
    if not user.whatsapp_enabled:
        return False
        
    if user.preferred_types:
        types = [t.strip().lower() for t in user.preferred_types.split(',')]
        if opp.type.lower() not in types:
            return False

    if user.interests:
        interests = [i.strip().lower() for i in user.interests.split(',')]
        opp_cat = (opp.category or "").lower()
        opp_title = opp.title.lower()
        match = False
        for i in interests:
            if i in opp_title or i in opp_cat:
                match = True
                break
        if not match:
            return False
            
    return True

def generate_alert_text(opp, rule_type):
    urgency = ""
    if '7_days' in rule_type or '3_days' in rule_type:
        urgency = "⚠️ Upcoming Deadline Reminder"
    elif '24_hours' in rule_type:
        urgency = "🚨 URGENT: 24 Hours Left!"
    elif 'today' in rule_type:
        urgency = "🔥 FINAL REMINDER: Deadline Today!"
    elif rule_type == 'new':
        urgency = "🆕 New Opportunity Alert"
        
    reg_date = opp.registration_deadline.strftime('%d %B %Y') if opp.registration_deadline else "N/A"
    sub_date = opp.submission_deadline.strftime('%d %B %Y') if opp.submission_deadline else "N/A"
    
    text = "🚨 *Opportunity Alert*\n\n"
    if urgency:
        text = f"{urgency}\n\n🚨 *Opportunity Alert*\n\n"
        
    text += f"*{opp.title}*\n\n"
    
    if opp.category:
        text += f"🎯 Category: {opp.category}\n"
    text += f"🏆 Type: {opp.type}\n"
    if opp.organizer:
        text += f"🏢 Organizer: {opp.organizer}\n"
        
    text += f"\n📅 Registration Deadline:\n{reg_date}\n"
    text += f"\n📝 Submission Deadline:\n{sub_date}\n"
    
    if opp.notification_date:
        text += f"\n📩 Notification Date:\n{opp.notification_date.strftime('%d %B %Y')}\n"
    if opp.camera_ready_deadline:
        text += f"\n📄 Camera-Ready:\n{opp.camera_ready_deadline.strftime('%d %B %Y')}\n"
        
    if opp.is_scopus_indexed:
        text += "\n✅ Verified Scopus-Indexed\n"
        
    text += f"\n🔗 Link: {opp.url}"
    return text

def send_whatsapp_alerts():
    upcoming_opportunities = Opportunity.query.all()
    subscribed_users = User.query.filter_by(whatsapp_enabled=True).all()
    
    alerts_sent = []
    now = datetime.utcnow()
    
    for opp in upcoming_opportunities:
        rules = []
        if (now - opp.created_at).total_seconds() < 86400:
            rules.append('new')
            
        rules.extend(check_rules('registration', opp.registration_deadline, now))
        rules.extend(check_rules('submission', opp.submission_deadline, now))
        rules.extend(check_rules('notification', opp.notification_date, now))
        rules.extend(check_rules('camera_ready', opp.camera_ready_deadline, now))
        
        for rule in rules:
            msg_text = generate_alert_text(opp, rule)
            
            for user in subscribed_users:
                if matches_preferences(user, opp):
                    history = AlertHistory.query.filter_by(user_id=user.id, opportunity_id=opp.id, alert_type=rule).first()
                    if history:
                        continue 
                    
                    new_alert = AlertHistory(user_id=user.id, opportunity_id=opp.id, alert_type=rule)
                    db.session.add(new_alert)
                    
                    user_phone = user.phone_number
                    alerts_sent.append(f"To {user.name} ({user_phone}):\n" + msg_text)
                    
                    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                    if telegram_token and str(user_phone).isdigit():
                        try:
                            import requests
                            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                            payload = {"chat_id": user_phone, "text": msg_text, "parse_mode": "Markdown"}
                            requests.post(url, json=payload, timeout=5)
                        except:
                            pass

                    webhook_url = os.environ.get('WEBHOOK_URL')
                    if webhook_url:
                        try:
                            import requests
                            clean_phone = user_phone.replace('whatsapp:', '').replace('+', '')
                            payload = {
                                "user_name": user.name,
                                "user_phone": clean_phone,
                                "message_text": msg_text
                            }
                            requests.post(webhook_url, json=payload, timeout=5)
                        except:
                            pass

    db.session.commit()

    if alerts_sent:
        log_data = []
        if os.path.exists(ALERTS_FILE):
            try:
                with open(ALERTS_FILE, 'r') as f:
                    log_data = json.load(f)
            except:
                pass
        log_data.append({'timestamp': datetime.utcnow().isoformat(), 'messages': alerts_sent})
        with open(ALERTS_FILE, 'w') as f:
            json.dump(log_data, f, indent=4)
            
    return alerts_sent
