from typing import Literal

SAMPLES: dict[Literal["write_query", "read_query", "create_table"], list[str]] = {
    "write_query": [
        "INSERT INTO users (id, name, email, create_date, update_timestamp, is_active) VALUES (1, 'John Doe', 'john@example.com', date '2023-10-01', timestamp '2023-10-02 12:00:00', TRUE);",
        "UPDATE users SET email = 'johndoe@example.com', update_timestamp = current_timestamp() WHERE id = 1;",
        "DELETE FROM users WHERE id = 1;"
    ],
    "read_query": [
        "SELECT * FROM users;",
        "SELECT id, name FROM users WHERE email LIKE '%@example.com';",
        "SELECT order_id, nvl(amount, 0) AS total_amount FROM orders;",
        "SELECT name, IFNULL(age, 'Unknown') AS age FROM student;",
        "SELECT name, score, multiIf(score >= 90, 'A', score >= 80, 'B', score >= 70, 'C', score >= 60, 'D') AS grade FROM (VALUES ('Alice', 92),('Bob', 85),('Charlie', 77),('David', 63),('Eve', 58)) students (name, score);",
    ],
    "create_table": [
        "CREATE TABLE users ("
        "id INT "
        "name STRING, "
        "email STRING, "
        "create_date date DEFAULT DATE(current_timestamp()), "
        "update_timestamp TIMESTAMP DEFAULT current_timestamp(), "
        "is_active BOOLEAN DEFAULT TRUE"
        ");",
    ]
}