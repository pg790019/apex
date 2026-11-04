import sqlite3

def fetch_employee_stats(db_path):
    """Connects to the database, executes the SQL query, and returns the results."""
    query = """SELECT department, COUNT(*) AS employee_count, AVG(salary) AS average_salary 
               FROM employees 
               WHERE salary > 50000 
               GROUP BY department 
               ORDER BY average_salary DESC;"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        return str(e)

# Example usage
if __name__ == "__main__":
    db_path = "employees.db"  # Path to your database
    stats = fetch_employee_stats(db_path)
    for row in stats:
        print(f"Department: {row[0]}, Employee Count: {row[1]}, Average Salary: {row[2]}")