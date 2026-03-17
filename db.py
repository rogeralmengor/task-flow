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
    duration = Column(Float, default=0.0)  # Total accumulated hours
    status = Column(String(20), default='todo')  # todo, running, paused, finished
    first_started_at = Column(DateTime, nullable=True)  # Absolute first start
    current_segment_start = Column(DateTime, nullable=True)  # Start of current active period
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
        if date is None:
            date = datetime.now()
        task = Task(agresso_code=agresso_code, activity=activity, date=date, status='todo')
        self.session.add(task)
        self.session.commit()
        return task
    
    def get_task_by_id(self, task_id):
        return self.session.query(Task).filter(Task.id == task_id).first()
    
    def get_todo_tasks(self):
        return self.session.query(Task).filter(Task.status == 'todo').order_by(Task.date.desc()).all()
    
    def get_running_task(self):
        """Returns task if it is either running or paused to show in 'Monitor'"""
        return self.session.query(Task).filter(Task.status.in_(['running', 'paused'])).first()
    
    def get_finished_tasks_today(self):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        return self.session.query(Task).filter(
            Task.status == 'finished',
            Task.finished_at >= today_start,
            Task.finished_at < today_end
        ).order_by(Task.finished_at.desc()).all()

    def get_finished_tasks_by_date_range(self, start_date, end_date):
        return self.session.query(Task).filter(
            Task.status == 'finished',
            Task.finished_at >= start_date,
            Task.finished_at < end_date
        ).order_by(Task.finished_at.asc()).all()
    
    # === TASK STATE MANAGEMENT ===
    
    def start_task(self, task_id):
        """Initial start of a TODO task"""
        running = self.get_running_task()
        if running:
            return None, "Another task is active. Pause or stop it first."
        
        task = self.get_task_by_id(task_id)
        if task and task.status == 'todo':
            now = datetime.now()
            task.status = 'running'
            task.first_started_at = now
            task.current_segment_start = now
            self.session.commit()
            return task, None
        return None, "Task not found or not in TODO state"
    
    def pause_task(self, task_id):
        """Stops the live clock and saves current segment time to duration"""
        task = self.get_task_by_id(task_id)
        if task and task.status == 'running':
            if task.current_segment_start:
                now = datetime.now()
                # Calculate hours spent in this specific segment
                elapsed = (now - task.current_segment_start).total_seconds() / 3600.0
                task.duration += elapsed
                task.current_segment_start = None # This freezes the live timer
            
            task.status = 'paused'
            self.session.commit()
            return task
        return None

    def resume_task(self, task_id):
        """Starts a fresh segment for a paused task"""
        task = self.get_task_by_id(task_id)
        if task and task.status == 'paused':
            task.status = 'running'
            task.current_segment_start = datetime.now() # Start new segment
            self.session.commit()
            return task
        return None
    
    def stop_task(self, task_id, finish=True):
        """Finalize task. If finish=True, moves to history."""
        task = self.get_task_by_id(task_id)
        if task and task.status in ['running', 'paused']:
            # If it was running, add the final segment to duration
            if task.status == 'running' and task.current_segment_start:
                now = datetime.now()
                elapsed = (now - task.current_segment_start).total_seconds() / 3600.0
                task.duration += elapsed
            
            if finish:
                task.status = 'finished'
                task.finished_at = datetime.now()
            else:
                # Reset to todo state
                task.status = 'todo'
                task.first_started_at = None
                task.duration = 0.0
            
            task.current_segment_start = None
            self.session.commit()
            return task
        return None

    # === UPDATE & DETAIL MANAGEMENT ===

    def update_task_details(self, task_id, code, activity, started_at_iso, finished_at_iso):
        """Full manual override for historical entries"""
        task = self.get_task_by_id(task_id)
        if task:
            try:
                start_dt = datetime.fromisoformat(started_at_iso.replace(' ', 'T'))
                end_dt = datetime.fromisoformat(finished_at_iso.replace(' ', 'T'))
                
                duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
                
                task.agresso_code = code
                task.activity = activity
                task.first_started_at = start_dt
                task.finished_at = end_dt
                task.duration = max(0, duration_hours)
                
                self.session.commit()
                return task
            except Exception as e:
                print(f"Error updating details: {e}")
                return None
        return None

    def update_task(self, task_id, agresso_code=None, activity=None):
        task = self.get_task_by_id(task_id)
        if task:
            if agresso_code: task.agresso_code = agresso_code
            if activity: task.activity = activity
            self.session.commit()
            return task
        return None
    
    def delete_task(self, task_id):
        task = self.get_task_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False
    
    # === STATISTICS ===
    
    def get_week_stats(self, year, week_number):
        # Calculate ISO week range
        jan_4 = datetime(year, 1, 4)
        week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
        first_day = week_1_monday + timedelta(weeks=week_number - 1)
        last_day = first_day + timedelta(days=7)
        
        tasks = self.get_finished_tasks_by_date_range(first_day, last_day)
        
        stats = {}
        total_hours = 0.0
        for task in tasks:
            key = task.agresso_code
            if key not in stats:
                stats[key] = {'agresso_code': key, 'total_hours': 0.0, 'tasks': []}
            stats[key]['total_hours'] += task.duration
            stats[key]['tasks'].append(task)
            total_hours += task.duration
        
        return {
            'week': week_number, 'year': year,
            'first_day': first_day, 'last_day': last_day,
            'stats': stats, 'total_hours': total_hours, 'tasks': tasks
        }

    def close(self):
        self.session.close()

if __name__ == "__main__":
    db = TimeTrackingDB()
    print("Database ready.")
    db.close()
