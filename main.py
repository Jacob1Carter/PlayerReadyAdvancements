# main.py

from flask import Flask, render_template, redirect, request
import sqlite3
import os

app = Flask(__name__)


# database setup
@app.before_request
def construct_db():
    # check that db exists
    if not os.path.exists("data/database.db"):
        with open("data/database.db", "w") as db_file:
            pass  # Create an empty database file
    # check users and advancements tables exist, if not create them
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS USERS (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, user_md5 TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS ADVANCEMENTS (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT)"
    )
    conn.commit()
    conn.close()


# admin required decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        # Check if user is admin
        # If not, redirect to main page or show error
        return f(*args, **kwargs)
    return decorated_function


# routes


@app.route("/", methods=["GET"])
def main():
    return render_template("main/main.html")


@app.route("/register", methods=["GET"])
def register():
    return render_template("main/login-register.html", mode="register")


@app.route("/register-input", methods=["POST"])
def register_input():
    first = request.form.get("first")
    last = request.form.get("last")
    prep_md5 = first.strip().lower() + last.strip().lower()
    user_md5 = prep_md5.encode("utf-8").hex()
    # Insert user into database
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO USERS (name, user_md5) VALUES (?, ?)", (first, user_md5))
    conn.commit()
    conn.close()
    # Redirect to advancements page
    return redirect("/advancements/" + user_md5)


@app.route("/login", methods=["GET"])
def login():
    # Check if there is a NotFound query parameter
    NotFound = True if request.args.get("NotFound") is not None else False
    return render_template("main/login-register.html", mode="login", NotFound=NotFound)


@app.route("/login-input", methods=["POST"])
def login_input():
    first = request.form.get("first")
    last = request.form.get("last")
    prep_md5 = first.strip().lower() + last.strip().lower()
    user_md5 = prep_md5.encode("utf-8").hex()
    # Check if user exists in database
    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USERS WHERE user_md5 = ?", (user_md5,))
    user = cursor.fetchone()
    conn.close()
    if user:
        # User exists, redirect to advancements page
        return redirect("/advancements/" + user_md5)
    else:
        # User does not exist, redirect to register page
        return redirect("/login?NotFound")


@app.route("/advancements/<user_md5>", methods=["GET"])
def advancements(user_md5):
    return render_template("main/advancements.html")


# admin routes


#@admin_required
@app.route("/admin", methods=["GET"])
def admin():
    return render_template("admin/main.html")


@app.route("/admin/database", methods=["GET", "POST"])
def database_inline():
    query = "SELECT * FROM USERS ORDER BY ID"
    error = None
    data = []
    column_names = []
    
    if request.method == "POST":
        query = request.form.get("query")
    
    # execute query, get data
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        
        # Check if this is a SELECT query (has description)
        if cursor.description:
            data = cursor.fetchall()
            # get column names
            column_names = [description[0] for description in cursor.description]
        else:
            # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
            conn.commit()  # Commit the changes
            data = []
            column_names = []
            # Optionally show affected rows count
            if cursor.rowcount > 0:
                data = [[f"Query executed successfully. {cursor.rowcount} row(s) affected."]]
                column_names = ["Result"]
            else:
                data = [["Query executed successfully."]]
                column_names = ["Result"]
                
    except sqlite3.Error as e:
        error = (f"Error executing query: {e}")
    finally:
        conn.close()

    return render_template("admin/database.html", query=query, data=data, error=error, column_names=column_names)


if __name__ == "__main__":
    app.run()

# /main.py