# main.py
import pandas as pd

def process_employee_data(data):
    df = pd.DataFrame(data)
    filtered = df[df['salary'] > 50000]
    result = (
        filtered.groupby('department')
        .agg(employee_count=('employee_id', 'size'), average_salary=('salary', 'mean'))
        .reset_index()
        .sort_values(by='average_salary', ascending=False)
    )
    return result

# Example usage with sample data
if __name__ == '__main__':
    sample_data = [
        {'employee_id': 1, 'department': 'HR', 'salary': 60000},
        {'employee_id': 2, 'department': 'IT', 'salary': 70000},
        {'employee_id': 3, 'department': 'HR', 'salary': 40000},
        {'employee_id': 4, 'department': 'Finance', 'salary': 80000},
        {'employee_id': 5, 'department': 'IT', 'salary': 55000},
    ]
    result = process_employee_data(sample_data)
    print(result)