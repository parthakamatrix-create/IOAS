import re

with open('notifier.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """def generate_alert_text(opp, rule_type):
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
    
    text = f"🚨 *Opportunity Alert*\\n\\n"
    if urgency:
        text = f"{urgency}\\n\\n🚨 *Opportunity Alert*\\n\\n"
        
    text += f"*{opp.title}*\\n\\n"
    
    if opp.category:
        text += f"🎯 Category: {opp.category}\\n"
    text += f"🏆 Type: {opp.type}\\n"
    if opp.organizer:
        text += f"🏢 Organizer: {opp.organizer}\\n"
        
    text += f"\\n📅 Registration Deadline:\\n{reg_date}\\n"
    text += f"\\n📝 Submission Deadline:\\n{sub_date}\\n"
    
    if opp.notification_date:
        text += f"\\n📩 Notification Date:\\n{opp.notification_date.strftime('%d %B %Y')}\\n"
    if opp.camera_ready_deadline:
        text += f"\\n📄 Camera-Ready:\\n{opp.camera_ready_deadline.strftime('%d %B %Y')}\\n"
        
    if opp.is_scopus_indexed:
        text += f"\\n✅ Verified Scopus-Indexed\\n"
        
    text += f"\\n🔗 Link: {opp.url}"
    return text"""

content = re.sub(r'def generate_alert_text\(opp, rule_type\):.*?return text', new_func, content, flags=re.DOTALL)
with open('notifier.py', 'w', encoding='utf-8') as f:
    f.write(content)
