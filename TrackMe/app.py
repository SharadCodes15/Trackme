import os
from datetime import date
from flask import Flask, render_template, request, jsonify
from models import db, User, Habit, DailyLog
from sqlalchemy import or_

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///trackme.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-123')

db.init_app(app)

@app.route('/')
def dashboard():
    """Main dashboard landing page."""
    from models import Subject, AttendanceRecord
    
    user = User.query.first()
    if not user:
        # Create demo user if not exists (handling first run)
        user = User(username='Sharad')
        db.session.add(user)
        db.session.commit()
    
    today = date.today()
    
    # --- 1. Habit Stats ---
    habits = Habit.query.filter(
        Habit.user_id == user.id,
        or_(Habit.is_recurring == True, Habit.target_date == today)
    ).all()
    
    pending_habits = []
    completed_count = 0
    
    for h in habits:
        log = DailyLog.query.filter_by(habit_id=h.id, date=today).first()
        completed = log.completed if log else False
        if completed:
            completed_count += 1
        else:
            pending_habits.append(h)
    
    completion_rate = int((completed_count / len(habits) * 100)) if habits else 0
    
    # --- 2. Attendance Stats ---
    total_present = AttendanceRecord.query.join(Subject).filter(
        Subject.user_id == user.id,
        AttendanceRecord.status == 'Present'
    ).count()
    
    total_absent = AttendanceRecord.query.join(Subject).filter(
        Subject.user_id == user.id,
        AttendanceRecord.status == 'Absent'
    ).count()
    
    total_records = total_present + total_absent
    attendance_percentage = round((total_present / total_records * 100), 1) if total_records > 0 else 0
    
    return render_template(
        'dashboard.html',
        user=user,
        today=today.strftime('%A, %d %B %Y'),
        completion_rate=completion_rate,
        pending_habits=pending_habits,
        attendance_percentage=attendance_percentage
    )

@app.route('/habits', methods=['GET', 'POST'])
def habits_page():
    # For demo, get the first user or create one (Same as before)
    user = User.query.first()
    if not user:
        user = User(username='Sharad')
        db.session.add(user)
        db.session.commit()
        # Seed some initial habits
        h1 = Habit(name='Morning Jog', is_recurring=True, user_id=user.id)
        h2 = Habit(name='Read 30 mins', is_recurring=True, user_id=user.id)
        db.session.add_all([h1, h2])
        db.session.commit()

    # Handle Add Task
    if request.method == 'POST':
        name = request.form.get('name')
        habit_type = request.form.get('type') # 'recurring' or 'today'
        
        if name:
            is_recurring = (habit_type == 'recurring')
            target_date = date.today() if not is_recurring else None
            
            new_habit = Habit(name=name, is_recurring=is_recurring, target_date=target_date, user_id=user.id)
            db.session.add(new_habit)
            db.session.commit()

    today = date.today()
    
    # 1. Fetch Today's Habits
    habits = Habit.query.filter(
        Habit.user_id == user.id,
        or_(
            Habit.is_recurring == True,
            Habit.target_date == today
        )
    ).all()
    
    habits_data = []
    completed_count = 0
    for h in habits:
        log = DailyLog.query.filter_by(habit_id=h.id, date=today).first()
        completed = log.completed if log else False
        if completed:
            completed_count += 1
        
        # Calculate streak (consecutive days completed)
        streak = 0
        if h.is_recurring:  # Only calculate streaks for recurring habits
            from datetime import timedelta
            check_date = today
            while True:
                log = DailyLog.query.filter_by(habit_id=h.id, date=check_date).first()
                if log and log.completed:
                    streak += 1
                    check_date -= timedelta(days=1)
                else:
                    break
            
        habits_data.append({
            'id': h.id,
            'name': h.name,
            'type': 'Daily' if h.is_recurring else 'One-time',
            'completed': completed,
            'streak': streak
        })
    
    completion_rate = int((completed_count / len(habits) * 100)) if habits else 0

    # 2. Calculate Last 7 Days Consistency
    from datetime import timedelta
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)] # Last 7 days including today
    chart_labels = [d.strftime('%a') for d in dates]
    chart_data = []
    
    for d in dates:
        # Get all habits active on that day? 
        # For simplicity in this demo, we'll check ALL recurring habits + specific habits for that day
        # But `target_date` habits from the past might be hard to query if we didn't store "active habits history".
        # Simplified logic: Count DailyLogs for that day vs Total Recurring Habits.
        # This is an approximation. A real system needs better history tracking.
        
        # Count potential habits for day 'd'
        potential_habits_count = Habit.query.filter(
            Habit.user_id == user.id,
             or_(
                Habit.is_recurring == True,
                Habit.target_date == d
            )
        ).count()
        
        if potential_habits_count == 0:
            chart_data.append(0)
            continue

        completed_logs = DailyLog.query.join(Habit).filter(
            Habit.user_id == user.id,
            DailyLog.date == d,
            DailyLog.completed == True
        ).count()
        
        percentage = int((completed_logs / potential_habits_count) * 100)
        chart_data.append(percentage)

    return render_template(
        'habits.html', 
        habits=habits_data, 
        today=today.strftime('%A, %b %d'),
        completion_rate=completion_rate,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@app.route('/toggle/<int:habit_id>', methods=['POST'])
def toggle_habit(habit_id):
    today = date.today()
    log = DailyLog.query.filter_by(habit_id=habit_id, date=today).first()
    
    if log:
        log.completed = not log.completed
        is_completed = log.completed
    else:
        log = DailyLog(habit_id=habit_id, date=today, completed=True)
        db.session.add(log)
        is_completed = True
        
    db.session.commit()
    
    return jsonify({'success': True, 'completed': is_completed, 'habit_id': habit_id})

@app.route('/api/delete_habit/<int:habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    
    # Manually delete associated logs since cascade isn't set on model
    DailyLog.query.filter_by(habit_id=habit_id).delete()
    
    db.session.delete(habit)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/timetable')
def timetable():
    """Placeholder route for timetable page."""
    return render_template('timetable.html')

@app.route('/attendance')
def attendance():
    """Attendance tracking page with subjects and analytics."""
    from models import Subject, AttendanceRecord
    user = User.query.first()
    subjects = Subject.query.filter_by(user_id=user.id).all() if user else []
    
    # Get today's attendance status for each subject
    today = date.today()
    for subject in subjects:
        record = AttendanceRecord.query.filter_by(subject_id=subject.id, date=today).first()
        subject.today_status = record.status if record else None
    
    return render_template('attendance.html', subjects=subjects, today=today)

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance for a subject."""
    from models import Subject, AttendanceRecord
    
    data = request.get_json()
    subject_id = data.get('subject_id')
    status = data.get('status')  # 'Present' or 'Absent'
    attendance_date = data.get('date', date.today().isoformat())
    
    # Parse the date
    attendance_date = date.fromisoformat(attendance_date)
    
    # Find or create attendance record
    record = AttendanceRecord.query.filter_by(
        subject_id=subject_id,
        date=attendance_date
    ).first()
    
    if record:
        record.status = status
    else:
        record = AttendanceRecord(
            subject_id=subject_id,
            date=attendance_date,
            status=status
        )
        db.session.add(record)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'subject_id': subject_id,
        'status': status,
        'date': attendance_date.isoformat()
    })

@app.route('/api/attendance-stats', methods=['GET'])
def get_attendance_stats():
    """Get attendance statistics for analytics."""
    from models import Subject, AttendanceRecord
    from sqlalchemy import func
    
    user = User.query.first()
    if not user:
        return jsonify({'overall': {}, 'bySubject': []})
    
    # Overall stats
    total_present = AttendanceRecord.query.join(Subject).filter(
        Subject.user_id == user.id,
        AttendanceRecord.status == 'Present'
    ).count()
    
    total_absent = AttendanceRecord.query.join(Subject).filter(
        Subject.user_id == user.id,
        AttendanceRecord.status == 'Absent'
    ).count()
    
    total_records = total_present + total_absent
    overall_percentage = round((total_present / total_records * 100), 1) if total_records > 0 else 0
    
    # By subject stats
    subjects = Subject.query.filter_by(user_id=user.id).all()
    by_subject = []
    
    for subject in subjects:
        present = AttendanceRecord.query.filter_by(
            subject_id=subject.id,
            status='Present'
        ).count()
        
        absent = AttendanceRecord.query.filter_by(
            subject_id=subject.id,
            status='Absent'
        ).count()
        
        total = present + absent
        percentage = round((present / total * 100), 1) if total > 0 else 0
        
        by_subject.append({
            'name': subject.name,
            'percentage': percentage,
            'present': present,
            'absent': absent
        })
    
    return jsonify({
        'overall': {
            'present': total_present,
            'absent': total_absent,
            'percentage': overall_percentage
        },
        'bySubject': by_subject
    })

@app.route('/api/subject_stats/<int:subject_id>', methods=['GET'])
def get_subject_stats(subject_id):
    """Get all-time attendance stats for a specific subject."""
    from models import AttendanceRecord
    
    # Calculate counts
    present_count = AttendanceRecord.query.filter_by(
        subject_id=subject_id, 
        status='Present'
    ).count()
    
    absent_count = AttendanceRecord.query.filter_by(
        subject_id=subject_id, 
        status='Absent'
    ).count()
    
    total = present_count + absent_count
    percentage = round((present_count / total * 100), 1) if total > 0 else 0
    
    return jsonify({
        'present': present_count,
        'absent': absent_count,
        'total': total,
        'percentage': percentage
    })

@app.route('/api/chart-data/<period>', methods=['GET'])
def get_chart_data(period):
    from sqlalchemy import func
    from datetime import timedelta
    import calendar
    
    today = date.today()
    user = User.query.first()
    if not user:
        return jsonify({'labels': [], 'data': [], 'pieData': []})

    # Get query parameters
    chart_type = request.args.get('chartType', 'bar')  # 'line', 'bar', 'pie'
    selected_month = request.args.get('month', str(today.month))  # 1-12
    selected_year = request.args.get('year', str(today.year))
    
    try:
        selected_month = int(selected_month)
        selected_year = int(selected_year)
    except:
        selected_month = today.month
        selected_year = today.year

    labels = []
    data_points = []
    pie_data = []

    if period == 'week':
        # Last 7 days with improved labels
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            labels.append(f"{d.strftime('%a')} {d.day}")  # e.g., "Mon 12"
            
            count = DailyLog.query.join(Habit).filter(
                Habit.user_id == user.id,
                DailyLog.date == d,
                DailyLog.completed == True
            ).count()
            data_points.append(count)
        
        # Pie chart: Breakdown by habit for last 7 days
        if chart_type == 'pie':
            start_date = today - timedelta(days=6)
            habit_counts = db.session.query(
                Habit.name,
                func.count(DailyLog.id).label('count')
            ).join(DailyLog).filter(
                Habit.user_id == user.id,
                DailyLog.date >= start_date,
                DailyLog.date <= today,
                DailyLog.completed == True
            ).group_by(Habit.name).all()
            
            pie_data = [{'label': h.name, 'value': h.count} for h in habit_counts]

    elif period == 'month':
        # Specific month selection
        num_days = calendar.monthrange(selected_year, selected_month)[1]
        for day in range(1, num_days + 1):
            labels.append(str(day))
            d = date(selected_year, selected_month, day)
            
            count = DailyLog.query.join(Habit).filter(
                Habit.user_id == user.id,
                DailyLog.date == d,
                DailyLog.completed == True
            ).count()
            data_points.append(count)
        
        # Pie chart: Breakdown by habit for selected month
        if chart_type == 'pie':
            start_date = date(selected_year, selected_month, 1)
            end_date = date(selected_year, selected_month, num_days)
            
            habit_counts = db.session.query(
                Habit.name,
                func.count(DailyLog.id).label('count')
            ).join(DailyLog).filter(
                Habit.user_id == user.id,
                DailyLog.date >= start_date,
                DailyLog.date <= end_date,
                DailyLog.completed == True
            ).group_by(Habit.name).all()
            
            pie_data = [{'label': h.name, 'value': h.count} for h in habit_counts]

    elif period == 'year':
        # Selected year, grouped by month
        for month in range(1, 13):
            labels.append(calendar.month_abbr[month])
            
            start_date = date(selected_year, month, 1)
            last_day = calendar.monthrange(selected_year, month)[1]
            end_date = date(selected_year, month, last_day)
            
            count = DailyLog.query.join(Habit).filter(
                Habit.user_id == user.id,
                DailyLog.date >= start_date,
                DailyLog.date <= end_date,
                DailyLog.completed == True
            ).count()
            data_points.append(count)
        
        # Pie chart: Breakdown by habit for selected year
        if chart_type == 'pie':
            start_date = date(selected_year, 1, 1)
            end_date = date(selected_year, 12, 31)
            
            habit_counts = db.session.query(
                Habit.name,
                func.count(DailyLog.id).label('count')
            ).join(DailyLog).filter(
                Habit.user_id == user.id,
                DailyLog.date >= start_date,
                DailyLog.date <= end_date,
                DailyLog.completed == True
            ).group_by(Habit.name).all()
            
            pie_data = [{'label': h.name, 'value': h.count} for h in habit_counts]

    return jsonify({
        'labels': labels,
        'data': data_points,
        'pieData': pie_data
    })

# Initialize DB
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
