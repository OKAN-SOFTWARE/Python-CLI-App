class Task:
    def __init__(self, name, priority):
        name = name.strip()
        if not name:
            raise ValueError("Task name cannot be empty.")
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            raise ValueError("Priority must be an integer from 1 to 5.") from None
        if not 1 <= priority <= 5:
            raise ValueError("Priority must be between 1 and 5.")
        self.name = name
        self.priority = priority

    def __str__(self):
        return f"[Priority {self.priority}] {self.name}"

class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, name, priority):
        task = Task(name, priority)
        self.tasks.append(task)
        self.tasks.sort(key=lambda x: x.priority)

    def list_tasks(self):
        if not self.tasks:
            print("No tasks found.")
        for i, task in enumerate(self.tasks):
            print(f"{i + 1}. {task}")

    def remove_task(self, index):
        if not 0 <= index < len(self.tasks):
            raise ValueError("Task number is out of range.")
        self.tasks.pop(index)

def print_menu():
    print("\nTask Tracker")
    print("1. Add task")
    print("2. List tasks")
    print("3. Remove task")
    print("4. Exit")

def main():
    manager = TaskManager()
    while True:
        print_menu()
        choice = input("Choose an option: ").strip()

        if choice == "1":
            name = input("Enter task name: ")
            while True:
                try:
                    priority = int(input("Enter priority (1-5): "))
                except ValueError:
                    print("Priority must be a number. Please enter an integer from 1 to 5.")
                    continue
                if not 1 <= priority <= 5:
                    print("Priority must be between 1 and 5.")
                    continue
                break
            try:
                manager.add_task(name, priority)
            except ValueError as error:
                print(error)
                continue
            print("Task added.")

        elif choice == "2":
            manager.list_tasks()

        elif choice == "3":
            manager.list_tasks()
            if not manager.tasks:
                continue
            try:
                task_number = int(input("Enter task number to remove: "))
            except ValueError:
                print("Task number must be an integer.")
                continue
            try:
                manager.remove_task(task_number - 1)
            except ValueError as error:
                print(error)
                continue
            print("Task removed.")

        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
