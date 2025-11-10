from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import calendar

Base = declarative_base()

class Task(Base):
    """Task model for time tracking"""
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agresso_code = Column(String(50), nullable=False)
    activity = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.now)
    duration = Column(Float, default=0.0)  # Duration in hours (only active time)
    status = Column(String(20), default='todo')  # todo, running, paused, finished
    first_started_at = Column(DateTime, nullable=True)  # When task was first started
    current_segment_start = Column(DateTime, nullable=True)  # Current running segment start
    finished_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Task(id={self.id}, agresso={self.agresso_code}, activity={self.activity}, status={self.status})>"


class TimeTrackingDB:
    """Database handler for time tracking"""
    
    def __init__(self, db_url='sqlite:///timetracking.db'):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    # === TASK CRUD OPERATIONS ===
    
    def add_task(self, agresso_code, activity, date=None):
        """Add a new task"""
        if date is None:
            date = datetime.now()
        task = Task(agresso_code=agresso_code, activity=activity, date=date, status='todo')
        self.session.add(task)
        self.session.commit()
        return task
    
    def get_task_by_id(self, task_id):
        """Get a specific task by ID"""
        return self.session.query(Task).filter(Task.id == task_id).first()
    
    def get_todo_tasks(self):
        """Get all TODO tasks"""
        return self.session.query(Task).filter(Task.status == 'todo').order_by(Task.date.desc()).all()
    
    def get_running_task(self):
        """Get the currently running task (should be only one)"""
        return self.session.query(Task).filter(Task.status.in_(['running', 'paused'])).first()
    
    def get_finished_tasks_today(self):
        """Get finished tasks for today"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        return self.session.query(Task).filter(
            Task.status == 'finished',
            Task.finished_at >= today_start,
            Task.finished_at < today_end
        ).order_by(Task.finished_at.desc()).all()
    
    def get_finished_tasks_by_date_range(self, start_date, end_date):
        """Get finished tasks within a date range"""
        return self.session.query(Task).filter(
            Task.status == 'finished',
            Task.finished_at >= start_date,
            Task.finished_at < end_date
        ).order_by(Task.finished_at.asc()).all()
    
    # === TASK STATE MANAGEMENT ===
    
    def start_task(self, task_id):
        """Start a task (set to running)"""
        # First, check if there's already a running task
        running = self.get_running_task()
        if running:
            return None, "Another task is already running. Pause or stop it first."
        
        task = self.get_task_by_id(task_id)
        if task and task.status == 'todo':
            task.status = 'running'
            now = datetime.now()
            task.first_started_at = now  # Record the first start time
            task.current_segment_start = now  # Start timing this segment
            self.session.commit()
            return task, None
        return None, "Task not found or not in TODO state"
    
    def pause_task(self, task_id):
        """Pause a running task"""
        task = self.get_task_by_id(task_id)
        if task and task.status == 'running':
            task.status = 'paused'
            # Calculate elapsed time for this segment and add to total duration
            if task.current_segment_start:
                elapsed = (datetime.now() - task.current_segment_start).total_seconds() / 3600
                task.duration += elapsed
                task.current_segment_start = None  # Clear segment start
            self.session.commit()
            return task
        return None
    
    def resume_task(self, task_id):
        """Resume a paused task"""
        task = self.get_task_by_id(task_id)
        if task and task.status == 'paused':
            task.status = 'running'
            task.current_segment_start = datetime.now()  # Start new timing segment
            self.session.commit()
            return task
        return None
    
    def stop_task(self, task_id, finish=True):
        """Stop a task and optionally mark as finished"""
        task = self.get_task_by_id(task_id)
        if task and task.status in ['running', 'paused']:
            # Calculate final duration if running
            if task.status == 'running' and task.current_segment_start:
                elapsed = (datetime.now() - task.current_segment_start).total_seconds() / 3600
                task.duration += elapsed
            
            if finish:
                task.status = 'finished'
                task.finished_at = datetime.now()
            else:
                task.status = 'todo'
            
            task.current_segment_start = None
            self.session.commit()
            return task
        return None
    
    def get_current_task_duration(self, task_id):
        """Get the current duration of a running/paused task (in hours)"""
        task = self.get_task_by_id(task_id)
        if not task:
            return 0.0
        
        duration = task.duration
        
        # Add current running segment time if the task is running
        if task.status == 'running' and task.current_segment_start:
            elapsed = (datetime.now() - task.current_segment_start).total_seconds() / 3600
            duration += elapsed
        
        return duration
    
    def get_current_task_elapsed_seconds(self, task_id):
        """Get elapsed time since first start (for display timer) in seconds"""
        task = self.get_task_by_id(task_id)
        if not task or not task.first_started_at:
            return 0
        
        # Calculate total elapsed time from first start to now
        elapsed = (datetime.now() - task.first_started_at).total_seconds()
        return int(elapsed)
    
    # === UPDATE OPERATIONS ===
    
    def update_task(self, task_id, agresso_code=None, activity=None, duration=None, date=None):
        """Update task details"""
        task = self.get_task_by_id(task_id)
        if task:
            if agresso_code is not None:
                task.agresso_code = agresso_code
            if activity is not None:
                task.activity = activity
            if duration is not None:
                task.duration = duration
            if date is not None:
                task.date = date
            self.session.commit()
            return task
        return None
    
    def delete_task(self, task_id):
        """Delete a task"""
        task = self.get_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
    
    # === STATISTICS ===
    
    def get_week_stats(self, year, week_number):
        """Get statistics for a specific week (ISO week)"""
        # Get first day of the week (Monday) using ISO calendar
        # ISO week starts on Monday
        jan_4 = datetime(year, 1, 4)  # Jan 4 is always in week 1
        week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
        first_day = week_1_monday + timedelta(weeks=week_number - 1)
        last_day = first_day + timedelta(days=7)
        
        tasks = self.get_finished_tasks_by_date_range(first_day, last_day)
        
        # Group by agresso code
        stats = {}
        total_hours = 0.0
        
        for task in tasks:
            key = task.agresso_code
            if key not in stats:
                stats[key] = {
                    'agresso_code': task.agresso_code,
                    'activities': [],
                    'total_hours': 0.0,
                    'tasks': []
                }
            
            stats[key]['activities'].append(task.activity)
            stats[key]['total_hours'] += task.duration
            stats[key]['tasks'].append(task)
            total_hours += task.duration
        
        return {
            'week': week_number,
            'year': year,
            'first_day': first_day,
            'last_day': last_day,
            'stats': stats,
            'total_hours': total_hours,
            'tasks': tasks
        }
    
    def get_current_week_stats(self):
        """Get statistics for the current week"""
        now = datetime.now()
        year, week, _ = now.isocalendar()
        return self.get_week_stats(year, week)
    
    def close(self):
        """Close the database session"""
        self.session.close()


if __name__ == "__main__":
    # Test the database
    db = TimeTrackingDB()
    
    print("Database initialized successfully!")
    print("\nAdding sample tasks...")
    
    db.add_task("PRJ-001", "Backend Development")
    db.add_task("PRJ-001", "Code Review")
    db.add_task("PRJ-002", "Meeting with Client")
    
    print("Sample tasks added!")
    
    todos = db.get_todo_tasks()
    print(f"\nTODO tasks: {len(todos)}")
    for task in todos:
        print(f"  - {task.agresso_code}: {task.activity}")
    
    db.close()
