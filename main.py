# main.py

from flask import Flask, render_template, redirect, request
import sqlite3
import os

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("data/database.db")
    conn.row_factory = sqlite3.Row  # Enable row factory for dict-like access
    return conn


# database setup
@app.before_request
def construct_db():
    # check that db exists
    if not os.path.exists("data/database.db"):
        with open("data/database.db", "w") as db_file:
            pass  # Create an empty database file
    # check users and advancements tables exist, if not create them
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS USERS (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, user_md5 TEXT)"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS ADVANCEMENTS (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, image TEXT)"
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
    return render_template("main/main.html", title="Home - Player Ready Advancements")


@app.route("/register", methods=["GET"])
def register():
    return render_template("main/login-register.html", title="Register - Player Ready Advancements", mode="register")


@app.route("/register-input", methods=["POST"])
def register_input():
    first = request.form.get("first")
    last = request.form.get("last")
    prep_md5 = first.strip().lower() + last.strip().lower()
    user_md5 = prep_md5.encode("utf-8").hex()
    # Insert user into database
    conn = get_db_connection()
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
    return render_template("main/login-register.html", title="Login - Player Ready Advancements", mode="login", NotFound=NotFound)


@app.route("/login-input", methods=["POST"])
def login_input():
    first = request.form.get("first")
    last = request.form.get("last")
    prep_md5 = first.strip().lower() + last.strip().lower()
    user_md5 = prep_md5.encode("utf-8").hex()
    # Check if user exists in database
    conn = get_db_connection()

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
    error = None
    # Find user's name from database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM USERS WHERE user_md5 = ?", (user_md5,))
        user = cursor.fetchone()
        if not user:
            # User not found, redirect to login with NotFound
            return redirect("/login?NotFound")
        user_name = user["name"]

        #get all advancements

        cursor.execute("SELECT * FROM ADVANCEMENTS ORDER BY ID")
        advancements = cursor.fetchall()
        conn.close()
    except sqlite3.Error as error:
        if not user_name:
            user_name = "Unknown User"

    return render_template("main/advancements.html", title=f"{user_name}'s Advancements - Player Ready Advancements", error=error, user_name=user_name, advancements=advancements)


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
    conn = get_db_connection()
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

@app.route("/admin/advancements", methods=["GET"])
def advancements_admin():
    return render_template("admin/advancements.html")


@app.route("/admin/advancements/list", methods=["GET"])
def advancements_list():
    # get advancements from database
    if request.args.get("error"):
        error = request.args.get("error")
    else:
        error = None
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ADVANCEMENTS ORDER BY ID")
        advancements = cursor.fetchall()
    except sqlite3.Error as error:
        advancements = []
    conn.close()
    
    if not advancements:
        error = "No advancements found."
    return render_template("/admin/advancements-list.html", advancements=advancements, error=error)


@app.route("/admin/advancements/layout", methods=["GET"])
def advancements_layout():
    return render_template("admin/advancements-layout.html")


@app.route("/admin/advancements/create", methods=["GET"])
def create_advancement():
    # get all image names from static/images/item and static/images/block directories
    item_images = os.listdir("static/images/items")
    block_images = os.listdir("static/images/blocks")

    return render_template("admin/create-advancement.html", item_images=item_images, block_images=block_images)


@app.route("/admin/advancements/edit/<int:advancement_id>", methods=["GET"])
def edit_advancement(advancement_id):
    return redirect(f"/admin/advancements/list?error=This feature is not implemented yet.")


@app.route("/admin/advancements/edit/<int:advancement_id>/submit", methods=["POST"])
def edit_advancement_submit(advancement_id):
    return redirect(f"/admin/advancements/list?error=This feature is not implemented yet.")


@app.route("/admin/advancements/delete/<int:advancement_id>", methods=["POST"])
def delete_advancement(advancement_id):
    return redirect(f"/admin/advancements/list?error=This feature is not implemented yet.")


@app.route("/admin/advancements/new", methods=["POST"])
def add_advancement():
    name = request.form.get("name")
    description = request.form.get("description")
    item_image = request.form.get("item-image-name")
    block_image = request.form.get("block-image-name")
    image = "items/" + item_image if item_image else "blocks/" + block_image
    if not name or not description or not image:
        return redirect("/admin/advancements?error=All fields are required.")

    # Insert new advancement into database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO ADVANCEMENTS (name, description, image) VALUES (?, ?, ?)",
            (name, description, image)
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        return redirect(f"/admin/advancements?error=Error adding advancement: {e}")

    conn.close()
    return redirect("/admin/advancements")


# add advancement


@app.route("/admin/RESET", methods=["GET"])
def reset_advancements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS USERS")
    cursor.execute("DROP TABLE IF EXISTS ADVANCEMENTS")
    conn.commit()
    conn.close()
    return redirect("/admin")


if __name__ == "__main__":
    app.run()

# /main.py