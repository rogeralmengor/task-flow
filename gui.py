from flask import Flask, render_template, jsonify, request, redirect, url_for
from db import TimeTrackingDB
from datetime import datetime
from collections import defaultdict
import os

class TimeTrackingApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.db = TimeTrackingDB()
        # Fallback to 'User' if no environment variable is found
        self.user_name = os.environ.get('USERNAME', os.environ.get('USER', 'almrog'))
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            running = self.db.get_running_task()
            todos = self.db.get_todo_tasks()
            finished = self.db.get_finished_tasks_today()
            return render_template('dashboard.html', user=self.user_name, running=running, todos=todos, finished=finished)

        @self.app.route('/stats')
        @self.app.route('/stats/<int:year>/<int:week>')
        def stats(year=None, week=None):
            if year is None or week is None:
                year, week, _ = datetime.now().isocalendar()
            
            stats_data = self.db.get_week_stats(year, week)
            tasks_by_date = defaultdict(list)
            
            for task in stats_data.get('tasks', []):
                if task.finished_at:
                    date_key = task.finished_at.strftime('%Y-%m-%d')
                    tasks_by_date[date_key].append(task)
            
            def format_duration(decimal_hours):
                h = int(decimal_hours)
                m = int((decimal_hours - h) * 60)
                return f"{h}h {m:02d}m"

            return render_template(
                'stats.html', 
                stats=stats_data, 
                tasks_by_date=dict(sorted(tasks_by_date.items(), reverse=True)), 
                year=year, 
                week=week, 
                format_duration=format_duration
            )

        # --- API Actions ---

        @self.app.route('/api/add', methods=['POST'])
        def add_task():
            code = request.form.get('code')
            activity = request.form.get('activity')
            if code and activity:
                self.db.add_task(code, activity)
            return redirect(url_for('index'))

        @self.app.route('/api/task/start/<int:task_id>', methods=['POST'])
        def start_task(task_id):
            self.db.start_task(task_id)
            return "", 204

        @self.app.route('/api/task/pause/<int:task_id>', methods=['POST'])
        def pause_task(task_id):
            self.db.pause_task(task_id)
            return "", 204

        # --- MISSING RESUME ROUTE ADDED HERE ---
        @self.app.route('/api/task/resume/<int:task_id>', methods=['POST'])
        def resume_task(task_id):
            self.db.resume_task(task_id)
            return "", 204

        @self.app.route('/api/task/stop/<int:task_id>', methods=['POST'])
        def stop_task(task_id):
            self.db.stop_task(task_id, finish=True)
            return "", 204

        # Updated to accept DELETE for the Stats page cleanup
        @self.app.route('/api/task/<int:task_id>', methods=['DELETE'])
        @self.app.route('/api/task/delete/<int:task_id>', methods=['POST'])
        def delete_task(task_id):
            self.db.delete_task(task_id)
            return "", 204

        @self.app.route('/api/task/edit-details/<int:task_id>', methods=['POST'])
        def edit_task_details(task_id):
            code = request.form.get('code')
            activity = request.form.get('activity')
            started_at = request.form.get('started_at')
            finished_at = request.form.get('finished_at')
            
            if all([code, activity, started_at, finished_at]):
                self.db.update_task_details(task_id, code, activity, started_at, finished_at)
            return "", 204

    def run(self):
        self.app.run(debug=True, port=5000, host='0.0.0.0')

if __name__ == "__main__":
    TimeTrackingApp().run()
