import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_name='actuarial_calculator.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Table des utilisateurs
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           username
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           password_hash
                           TEXT
                           NOT
                           NULL,
                           email
                           TEXT,
                           created_at
                           DATETIME
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        # Table des calculs sauvegardés
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS calculations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER,
                           calculation_type
                           TEXT
                           NOT
                           NULL,
                           input_data
                           TEXT
                           NOT
                           NULL,
                           result_data
                           TEXT
                           NOT
                           NULL,
                           created_at
                           DATETIME
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       )
                           )
                       ''')

        conn.commit()
        conn.close()

    def save_calculation(self, user_id, calculation_type, input_data, result_data):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
                       INSERT INTO calculations (user_id, calculation_type, input_data, result_data)
                       VALUES (?, ?, ?, ?)
                       ''', (user_id, calculation_type, input_data, result_data))

        conn.commit()
        conn.close()
        return cursor.lastrowid

    def get_user_calculations(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT id, calculation_type, input_data, result_data, created_at
                       FROM calculations
                       WHERE user_id = ?
                       ORDER BY created_at DESC
                       ''', (user_id,))

        calculations = cursor.fetchall()
        conn.close()
        return calculations

    def create_user(self, username, password_hash, email=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           INSERT INTO users (username, password_hash, email)
                           VALUES (?, ?, ?)
                           ''', (username, password_hash, email))

            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None

    def get_user_by_username(self, username):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT id, username, password_hash, email
                       FROM users
                       WHERE username = ?
                       ''', (username,))

        user = cursor.fetchone()
        conn.close()
        return user