from flask import Flask, render_template, jsonify, request, redirect, url_for
from db import TimeTrackingDB
from datetime import datetime
from collections import defaultdict
import os

class TimeTrackingApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.db = TimeTrackingDB()
        # Fallback to 'almrog' if no env var is found to match your screenshot
        self.user_name = os.environ.get('USERNAME', os.environ.get('USER', 'almrog'))
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            """Main Dashboard View"""
            running = self.db.get_running_task()
            todos = self.db.get_todo_tasks()
            finished = self.db.get_finished_tasks_today()
            return render_template(
                'dashboard.html', 
                user=self.user_name, 
                running=running, 
                todos=todos, 
                finished=finished
            )

        @self.app.route('/stats')
        @self.app.route('/stats/<int:year>/<int:week>')
        def stats(year=None, week=None):
            """Weekly Statistics View with Navigation and TUI-style formatting"""
            if year is None or week is None:
                year, week, _ = datetime.now().isocalendar()
            
            # Get raw data from DB
            stats_data = self.db.get_week_stats(year, week)
            
            # Group tasks by date for the "DETAILED TASK LIST" (Logic from TUI)
            tasks_by_date = defaultdict(list)
            for task in stats_data.get('tasks', []):
                # Ensure the key is a string date for grouping
                date_key = task.finished_at.strftime('%Y-%m-%d')
                tasks_by_date[date_key].append(task)
            
            # Helper function to convert decimal hours to "Xh Ym" (Logic from TUI)
            def format_duration(decimal_hours):
                h = int(decimal_hours)
                m = int((decimal_hours - h) * 60)
                return f"{h}h {m:02d}m"

            return render_template(
                'stats.html', 
                stats=stats_data, 
                tasks_by_date=dict(sorted(tasks_by_date.items())), # Sorted chronologically
                year=year, 
                week=week,
                format_duration=format_duration # Passed to template for rendering
            )

        # --- API Actions ---

        @self.app.route('/api/add', methods=['POST'])
        def add_task():
            """Creates a new task in the TODO list"""
            code = request.form.get('code')
            activity = request.form.get('activity')
            if code and activity:
                self.db.add_task(code, activity)
            return redirect(url_for('index'))

        @self.app.route('/api/task/start/<int:task_id>', methods=['POST'])
        def start_task(task_id):
            """Starts a task by ID"""
            self.db.start_task(task_id)
            return "", 204

        @self.app.route('/api/task/stop/<int:task_id>', methods=['POST'])
        def stop_task(task_id):
            """Stops the currently running task and marks it as finished"""
            self.db.stop_task(task_id, finish=True)
            return "", 204

    def run(self):
        """Starts the Flask Web Server"""
        self.app.run(debug=True, port=5000)

if __name__ == "__main__":
    app_instance = TimeTrackingApp()
    app_instance.run()
