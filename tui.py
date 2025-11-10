from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Button, Input, Label, RichLog
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from datetime import datetime
from db import TimeTrackingDB
import os

# Get user's name from environment or use default
USER_NAME = os.environ.get('USERNAME', os.environ.get('USER', 'User'))

class ConfirmDialog(ModalScreen):
    """A simple confirmation dialog"""
    
    def __init__(self, message, on_yes, on_no=None):
        super().__init__()
        self.message = message
        self.on_yes_callback = on_yes
        self.on_no_callback = on_no
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.message, id="dialog-message")
            with Horizontal(id="dialog-buttons"):
                yield Button("Yes", variant="success", id="btn-yes")
                yield Button("No", variant="error", id="btn-no")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            if self.on_yes_callback:
                self.on_yes_callback()
        else:
            if self.on_no_callback:
                self.on_no_callback()
        self.dismiss()


class AddTaskScreen(Screen):
    """Screen for adding a new task"""
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="add-form"):
            yield Label("Add New Task", id="form-title")
            yield Label("Agresso Code:")
            yield Input(placeholder="PRJ-001", id="agresso-code")
            yield Label("Activity Description:")
            yield Input(placeholder="Backend Development", id="activity")
            yield Button("Add Task", variant="success", id="submit-task")
            yield Label("", id="task-message")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-task":
            try:
                agresso = self.query_one("#agresso-code", Input).value.strip()
                activity = self.query_one("#activity", Input).value.strip()
                
                if not agresso or not activity:
                    self.query_one("#task-message", Label).update("✗ All fields are required!")
                    return
                
                self.app.db.add_task(agresso, activity)
                
                self.query_one("#task-message", Label).update("✓ Task added successfully!")
                self.query_one("#agresso-code", Input).value = ""
                self.query_one("#activity", Input).value = ""
                self.app.refresh_data()
                    
            except Exception as e:
                self.query_one("#task-message", Label).update(f"✗ Error: {str(e)}")


class EditTaskScreen(Screen):
    """Screen for editing a finished task"""
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    
    def __init__(self, task):
        super().__init__()
        self.task = task
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="add-form"):
            yield Label("Edit Task", id="form-title")
            yield Label("Agresso Code:")
            yield Input(placeholder="PRJ-001", id="agresso-code", value=self.task.agresso_code)
            yield Label("Activity Description:")
            yield Input(placeholder="Backend Development", id="activity", value=self.task.activity)
            yield Label("Duration (hours):")
            yield Input(placeholder="1.5", id="duration", value=str(self.task.duration))
            yield Button("Save Changes", variant="success", id="submit-edit")
            yield Label("", id="edit-message")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-edit":
            try:
                agresso = self.query_one("#agresso-code", Input).value.strip()
                activity = self.query_one("#activity", Input).value.strip()
                duration_str = self.query_one("#duration", Input).value.strip()
                
                if not agresso or not activity or not duration_str:
                    self.query_one("#edit-message", Label).update("✗ All fields are required!")
                    return
                
                duration = float(duration_str)
                self.app.db.update_task(self.task.id, agresso, activity, duration)
                
                self.query_one("#edit-message", Label).update("✓ Task updated successfully!")
                self.app.refresh_data()
                self.app.pop_screen()
                    
            except ValueError:
                self.query_one("#edit-message", Label).update("✗ Duration must be a number!")
            except Exception as e:
                self.query_one("#edit-message", Label).update(f"✗ Error: {str(e)}")


class WeeklyStatsScreen(Screen):
    """Screen for displaying weekly statistics"""
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    
    def __init__(self, week=None, year=None):
        super().__init__()
        from datetime import datetime
        if week is None or year is None:
            now = datetime.now()
            self.year, self.week, _ = now.isocalendar()
        else:
            self.week = week
            self.year = year
    
    def compose(self) -> ComposeResult:
        from textual.widgets import RichLog
        from textual.containers import ScrollableContainer
        
        yield Header()
        with Container(id="stats-container"):
            yield Label(f"[bold cyan]📊 Weekly Statistics - KW {self.week}/{self.year}[/]", id="stats-title")
            with Horizontal(id="stats-nav"):
                yield Button("◀ Prev Week", variant="primary", id="btn-prev-week")
                yield Button("Current Week", variant="success", id="btn-current-week")
                yield Button("Next Week ▶", variant="primary", id="btn-next-week")
            with ScrollableContainer(id="stats-content"):
                yield RichLog(id="stats-output", highlight=True, markup=True)
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_stats()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        from datetime import datetime, timedelta
        
        if event.button.id == "btn-prev-week":
            # Go to previous week
            date = datetime.strptime(f'{self.year}-W{self.week}-1', "%Y-W%W-%w")
            date = date - timedelta(days=7)
            self.year, self.week, _ = date.isocalendar()
            self.refresh_stats()
        
        elif event.button.id == "btn-next-week":
            # Go to next week
            date = datetime.strptime(f'{self.year}-W{self.week}-1', "%Y-W%W-%w")
            date = date + timedelta(days=7)
            self.year, self.week, _ = date.isocalendar()
            self.refresh_stats()
        
        elif event.button.id == "btn-current-week":
            now = datetime.now()
            self.year, self.week, _ = now.isocalendar()
            self.refresh_stats()
    
    def refresh_stats(self):
        """Generate and display weekly statistics"""
        from collections import defaultdict
        
        output = self.query_one("#stats-output", RichLog)
        output.clear()
        
        # Update title
        self.query_one("#stats-title", Label).update(
            f"[bold cyan]📊 Weekly Statistics - KW {self.week}/{self.year}[/]"
        )
        
        stats = self.app.db.get_week_stats(self.year, self.week)
        
        output.write(f"[bold]Period:[/] {stats['first_day'].strftime('%d.%m.%Y')} - {stats['last_day'].strftime('%d.%m.%Y')}")
        output.write("")
        
        if not stats['tasks']:
            output.write("[yellow]❌ No tasks recorded for this week.[/]")
            return
        
        # Group tasks by date
        tasks_by_date = defaultdict(list)
        for task in stats['tasks']:
            date_key = task.finished_at.strftime('%Y-%m-%d')
            tasks_by_date[date_key].append(task)
        
        # Display detailed task list
        output.write("[bold yellow]📋 DETAILED TASK LIST[/]")
        output.write("─" * 70)
        
        for date_key in sorted(tasks_by_date.keys()):
            tasks = tasks_by_date[date_key]
            date_obj = datetime.strptime(date_key, '%Y-%m-%d')
            date_str = date_obj.strftime('%a, %d.%m')
            
            daily_total = 0.0
            output.write(f"\n[bold cyan]{date_str}[/]")
            
            for task in tasks:
                hours = int(task.duration)
                minutes = int((task.duration - hours) * 60)
                output.write(f"  [green]{task.agresso_code:<12}[/] {task.activity[:40]:<40} [yellow]{hours}h {minutes:02d}m[/]")
                daily_total += task.duration
            
            hours = int(daily_total)
            minutes = int((daily_total - hours) * 60)
            output.write(f"  [dim]Daily Total: {hours}h {minutes:02d}m[/]")
        
        output.write("\n" + "=" * 70)
        
        # Summary by Agresso Code
        output.write("\n[bold yellow]💼 SUMMARY BY AGRESSO CODE[/]")
        output.write("─" * 70)
        
        for code, data in sorted(stats['stats'].items()):
            hours = int(data['total_hours'])
            minutes = int((data['total_hours'] - hours) * 60)
            percentage = (data['total_hours'] / stats['total_hours'] * 100) if stats['total_hours'] > 0 else 0
            
            output.write(f"[bold green]{code:<15}[/] [yellow]{hours}h {minutes:02d}m[/]  ({len(data['tasks'])} tasks)  [cyan]{percentage:>5.1f}%[/]")
        
        output.write("─" * 70)
        total_h = int(stats['total_hours'])
        total_m = int((stats['total_hours'] - total_h) * 60)
        output.write(f"[bold]TOTAL: {total_h}h {total_m:02d}m[/]")
        output.write("=" * 70)
        
        # ASCII Pie Chart
        output.write("\n[bold yellow]📊 TIME DISTRIBUTION[/]")
        total = stats['total_hours']
        if total > 0:
            for code, data in sorted(stats['stats'].items(), key=lambda x: x[1]['total_hours'], reverse=True):
                percentage = (data['total_hours'] / total) * 100
                bar_length = int((data['total_hours'] / total) * 30)
                bar = "█" * bar_length
                hours = int(data['total_hours'])
                minutes = int((data['total_hours'] - hours) * 60)
                output.write(f"{code:<12} [cyan]{bar:<30}[/] {percentage:>5.1f}%  ({hours}h {minutes:02d}m)")
        
        output.write("\n" + "=" * 70)
        
        # Agresso Summary
        output.write("\n[bold yellow]📝 AGRESSO WEEKLY SUMMARY[/]")
        output.write("[dim](Copy this to Agresso)[/]")
        output.write("=" * 70)
        output.write(f"KW {self.week}/{self.year}")
        output.write(f"Total Hours: {total_h}h {total_m:02d}m")
        output.write("")
        
        for code, data in sorted(stats['stats'].items()):
            unique_activities = list(set(data['activities']))
            activities_str = ", ".join(unique_activities[:3])
            if len(unique_activities) > 3:
                activities_str += f" (+ {len(unique_activities)-3} more)"
            
            hours = int(data['total_hours'])
            minutes = int((data['total_hours'] - hours) * 60)
            
            output.write(f"[green]Code:[/] {code}")
            output.write(f"  [cyan]Activities:[/] {activities_str}")
            output.write(f"  [yellow]Time:[/] {hours}h {minutes:02d}m")
            output.write("")
        
        output.write("=" * 70)


class TimeTrackingApp(App):
    """Main Time Tracking Application"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #dashboard {
        height: 100%;
        padding: 1;
    }
    
    .panel {
        border: solid $primary;
        height: auto;
        margin: 1;
        padding: 1;
    }
    
    #header-bar {
        height: 4;
        margin: 1;
        padding: 1;
        border: solid $accent;
        background: $boost;
    }
    
    #user-info {
        text-style: bold;
        color: $accent;
    }
    
    #date-info {
        text-align: right;
        color: $text;
    }
    
    #main-content {
        height: 1fr;
    }
    
    #current-task-panel {
        width: 1fr;
        height: 100%;
    }
    
    #todo-panel {
        width: 2fr;
        height: 100%;
    }
    
    #finished-panel {
        height: 15;
    }
    
    #add-form {
        width: 60;
        height: auto;
        margin: 2 4;
        padding: 2;
        border: solid $primary;
    }
    
    #form-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        content-align: center middle;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    Button {
        margin-top: 1;
        width: 100%;
    }
    
    DataTable {
        height: 100%;
    }
    
    #task-message, #edit-message {
        margin-top: 1;
        text-align: center;
    }
    
    #current-task-info {
        margin: 1;
        padding: 1;
        border: solid $accent;
        background: $boost;
        height: auto;
    }
    
    #dialog {
        width: 50;
        height: 11;
        margin: 10 25;
        padding: 2;
        border: solid $accent;
        background: $surface;
    }
    
    #dialog-message {
        margin-bottom: 2;
        text-align: center;
    }
    
    #dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    
    #dialog-buttons Button {
        margin: 0 1;
        width: 15;
    }
    
    #stats-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    #stats-title {
        text-align: center;
        margin: 1;
        text-style: bold;
    }
    
    #stats-nav {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1;
    }
    
    #stats-nav Button {
        margin: 0 1;
        min-width: 18;
    }
    
    #stats-content {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #stats-output {
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("a", "add_task", "Add Task"),
        Binding("t", "start_selected_task", "Start Task"),
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("s", "stop_task", "Stop Task"),
        Binding("w", "weekly_stats", "Weekly Stats"),
        Binding("e", "edit_task", "Edit Task"),
        Binding("d", "delete_task", "Delete"),
        Binding("ctrl+w", "switch_focus", "Switch Panel"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]
    
    TITLE = "Agresso Time Tracker"
    
    def __init__(self):
        super().__init__()
        self.db = TimeTrackingDB()
        self.selected_todo_id = None
        self.selected_finished_id = None
        self.current_focus = "todo"  # "todo" or "finished"
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="dashboard"):
            # Header with user info and date
            with Container(id="header-bar"):
                with Horizontal():
                    yield Static(f"[bold cyan]👤 {USER_NAME}[/]", id="user-info")
                    yield Static("", id="date-info")
            
            # Main content area
            with Horizontal(id="main-content"):
                # Left: Current Task
                with Vertical(id="current-task-panel", classes="panel"):
                    yield Label("[bold yellow]⏱️  Current Task[/]")
                    yield Static("No task running", id="current-task-info")
                
                # Right: TODO Tasks
                with Vertical(id="todo-panel", classes="panel"):
                    yield Label("[bold green]📋 TODO Tasks[/]")
                    yield DataTable(id="todo-table")
            
            # Bottom: Finished Tasks Today
            with Container(id="finished-panel", classes="panel"):
                yield Label("[bold blue]✅ Finished Tasks Today[/]")
                yield DataTable(id="finished-table")
        
        yield Footer()
    
    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1, self.update_current_task_display)
        self.refresh_data()
        # Set initial focus on todo table
        try:
            todo_table = self.query_one("#todo-table", DataTable)
            todo_table.focus()
            todo_table.cursor_type = "row"
        except Exception:
            pass
    
    def update_date_display(self) -> None:
        """Update the date display"""
        try:
            now = datetime.now()
            date_str = now.strftime("%A, %B %d, %Y - KW %V")
            self.query_one("#date-info", Static).update(date_str)
        except Exception:
            # Widget not mounted yet, skip update
            pass
    
    def update_current_task_display(self) -> None:
        """Update the current running task display"""
        try:
            running_task = self.db.get_running_task()
            
            if running_task:
                # Active duration (only work time, no pauses)
                duration = self.db.get_current_task_duration(running_task.id)
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                seconds = int(((duration - hours) * 60 - minutes) * 60)
                
                # Elapsed time since first start (wall clock time)
                elapsed_seconds = self.db.get_current_task_elapsed_seconds(running_task.id)
                elapsed_hours = elapsed_seconds // 3600
                elapsed_minutes = (elapsed_seconds % 3600) // 60
                elapsed_secs = elapsed_seconds % 60
                
                status_icon = "▶️" if running_task.status == "running" else "⏸️"
                status_text = "RUNNING" if running_task.status == "running" else "PAUSED"
                
                # Format start time (first time task was started)
                start_time = running_task.first_started_at.strftime("%H:%M") if running_task.first_started_at else "--:--"
                
                # Current time
                current_time = datetime.now().strftime("%H:%M:%S")
                
                info = f"""[bold]{status_icon} {status_text}[/]

[cyan]Code:[/] {running_task.agresso_code}
[cyan]Activity:[/] {running_task.activity[:40]}

[yellow]⏱️  Active Time:[/] [bold]{hours:02d}h {minutes:02d}m {seconds:02d}s[/]
[dim]Elapsed:[/] {elapsed_hours:02d}h {elapsed_minutes:02d}m {elapsed_secs:02d}s

[green]Started:[/] {start_time}  [blue]Now:[/] {current_time}

[dim]Space: Pause/Resume | S: Stop[/]"""
                
                self.query_one("#current-task-info", Static).update(info)
            else:
                self.query_one("#current-task-info", Static).update(
                    "[dim]No task running\n\nSelect a TODO task\nand press 't' to start[/]"
                )
        except Exception:
            # Widget not mounted yet, skip update
            pass
    
    def refresh_data(self) -> None:
        """Refresh all data displays"""
        try:
            self.update_date_display()
            
            # Update TODO table
            todo_table = self.query_one("#todo-table", DataTable)
            todo_table.clear(columns=True)
            todo_table.add_columns("ID", "Agresso Code", "Activity")
            todo_table.cursor_type = "row"
            
            todos = self.db.get_todo_tasks()
            for task in todos:
                todo_table.add_row(
                    str(task.id),
                    task.agresso_code,
                    task.activity[:40] + "..." if len(task.activity) > 40 else task.activity
                )
            
            # Update Finished table
            finished_table = self.query_one("#finished-table", DataTable)
            finished_table.clear(columns=True)
            finished_table.add_columns("ID", "Code", "Activity", "Start", "End", "Duration")
            finished_table.cursor_type = "row"
            
            finished = self.db.get_finished_tasks_today()
            for task in finished:
                hours = int(task.duration)
                minutes = int((task.duration - hours) * 60)
                
                # Use first_started_at for start time, finished_at for end time
                start_time = task.first_started_at.strftime("%H:%M") if task.first_started_at else "--:--"
                end_time = task.finished_at.strftime("%H:%M") if task.finished_at else "--:--"
                
                finished_table.add_row(
                    str(task.id),
                    task.agresso_code,
                    task.activity[:25] + "..." if len(task.activity) > 25 else task.activity,
                    start_time,
                    end_time,
                    f"{hours}h {minutes:02d}m"
                )
            
            self.update_current_task_display()
                
        except Exception as e:
            self.notify(f"Error refreshing data: {str(e)}", severity="error")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in tables"""
        if event.data_table.id == "todo-table":
            row_key = event.row_key
            cells = event.data_table.get_row(row_key)
            self.selected_todo_id = int(cells[0])
            self.current_focus = "todo"
        
        elif event.data_table.id == "finished-table":
            row_key = event.row_key
            cells = event.data_table.get_row(row_key)
            self.selected_finished_id = int(cells[0])
            self.current_focus = "finished"
    
    def action_start_selected_task(self) -> None:
        """Start the selected TODO task with 't' key"""
        if self.selected_todo_id and self.current_focus == "todo":
            task, error = self.db.start_task(self.selected_todo_id)
            if error:
                self.notify(error, severity="warning")
            else:
                self.notify(f"Started: {task.activity}")
                self.refresh_data()
        else:
            self.notify("Select a TODO task first", severity="warning")
    
    def action_switch_focus(self) -> None:
        """Switch focus between TODO and Finished tables (Ctrl+W)"""
        try:
            if self.current_focus == "todo":
                finished_table = self.query_one("#finished-table", DataTable)
                finished_table.focus()
                self.current_focus = "finished"
                self.notify("Switched to Finished Tasks")
            else:
                todo_table = self.query_one("#todo-table", DataTable)
                todo_table.focus()
                self.current_focus = "todo"
                self.notify("Switched to TODO Tasks")
        except Exception:
            pass
    
    def action_add_task(self) -> None:
        """Open add task screen"""
        self.push_screen(AddTaskScreen())
    
    def action_toggle_pause(self) -> None:
        """Pause or resume current task"""
        running_task = self.db.get_running_task()
        if running_task:
            if running_task.status == 'running':
                self.db.pause_task(running_task.id)
                self.notify("Task paused")
            elif running_task.status == 'paused':
                self.db.resume_task(running_task.id)
                self.notify("Task resumed")
            self.refresh_data()
        else:
            self.notify("No task is running", severity="warning")
    
    def action_stop_task(self) -> None:
        """Stop current task"""
        running_task = self.db.get_running_task()
        if running_task:
            def finish_task():
                self.db.stop_task(running_task.id, finish=True)
                duration = running_task.duration
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                self.notify(f"Task finished! Duration: {hours}h {minutes:02d}m")
                self.refresh_data()
            
            def cancel_task():
                self.db.stop_task(running_task.id, finish=False)
                self.notify("Task stopped (not finished)")
                self.refresh_data()
            
            self.push_screen(
                ConfirmDialog("Mark task as finished?", finish_task, cancel_task)
            )
        else:
            self.notify("No task is running", severity="warning")
    
    def action_edit_task(self) -> None:
        """Edit a finished task"""
        if self.selected_finished_id:
            task = self.db.get_task_by_id(self.selected_finished_id)
            if task:
                self.push_screen(EditTaskScreen(task))
        else:
            self.notify("Select a finished task first", severity="warning")
    
    def action_delete_task(self) -> None:
        """Delete a TODO task"""
        if self.selected_todo_id:
            def do_delete():
                self.db.delete_task(self.selected_todo_id)
                self.notify("Task deleted")
                self.refresh_data()
            
            self.push_screen(
                ConfirmDialog("Delete this task?", do_delete)
            )
        else:
            self.notify("Select a TODO task first", severity="warning")
    
    def action_refresh(self) -> None:
        """Refresh all data"""
        self.refresh_data()
        self.notify("Data refreshed!")
    
    def action_weekly_stats(self) -> None:
        """Open weekly statistics screen"""
        self.push_screen(WeeklyStatsScreen())


if __name__ == "__main__":
    app = TimeTrackingApp()
    app.run()
