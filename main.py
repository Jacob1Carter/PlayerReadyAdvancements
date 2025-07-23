# main.py

from flask import Flask, render_template, redirect, request
import sqlite3
import os
import json

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
        "CREATE TABLE IF NOT EXISTS USERS (ID INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, user_md5 TEXT, advancements text DEFAULT '[]')"
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

    with open("data/layout.json", "r") as f:
        layout_data = json.load(f)

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

    return render_template("main/advancements.html", title=f"{user_name}'s Advancements - Player Ready Advancements", error=error, layout=layout_data, user_name=user_name, advancements=advancements)


@app.route("/advancement-detail/<int:advancement_id>", methods=["GET"])
def advancement_detail(advancement_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ADVANCEMENTS WHERE ID = ?", (advancement_id,))
    advancement = cursor.fetchone()
    conn.close()
    if not advancement:
        return 404
    
    return render_template("main/advancement-detail.html", title=f"{advancement['name']} - Player Ready Advancements", advancement=advancement)


@app.route("/advancement/<int:advancement_id>/claim", methods=["POST"])
def claim_advancement(advancement_id):
    user_md5 = request.form.get("user_md5")
    if not user_md5:
        return redirect("/login?NotFound")

    # Get user's advancements
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT advancements FROM USERS WHERE user_md5 = ?", (user_md5,))
    user = cursor.fetchone()
    
    if not user:
        return redirect("/login?NotFound")

    advancements = json.loads(user["advancements"])
    
    # Check if advancement is already claimed
    if advancement_id in advancements:
        return redirect(f"/advancements/{user_md5}?error=Advancement already claimed.")

    # Add advancement to user's advancements
    advancements.append(advancement_id)
    
    # Update user's advancements in database
    cursor.execute("UPDATE USERS SET advancements = ? WHERE user_md5 = ?", (json.dumps(advancements), user_md5))
    conn.commit()
    conn.close()

    return redirect(f"/advancements/{user_md5}")


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
    with open("data/layout.json", "r") as f:
        layout_data = json.load(f)
    
    #get all advancements from database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ADVANCEMENTS ORDER BY ID")
        advancements = cursor.fetchall()
    except sqlite3.Error as error:
        advancements = []
    conn.close()

    return render_template("admin/advancements-layout.html", layout=layout_data, advancements=advancements)


@app.route("/admin/advancements/create", methods=["GET"])
def create_advancement():
    # get all image names from static/images/item and static/images/block directories
    item_images = os.listdir("static/images/items")
    block_images = os.listdir("static/images/blocks")

    return render_template("admin/create-advancement.html", item_images=item_images, block_images=block_images)


@app.route("/admin/assets", methods=["GET"])
def advancements_assets():
    error = request.args.get("error")
    if not error:
        error = None
    
    # get all asset names from static/images/items and static/images/blocks directories
    item_assets = os.listdir("static/images/items")
    block_assets = os.listdir("static/images/blocks")

    return render_template("admin/assets.html", error=error, item_assets=item_assets, block_assets=block_assets)


@app.route("/admin/advancements/edit/<int:advancement_id>", methods=["GET"])
def edit_advancement(advancement_id):
    error = request.args.get("error")
    if not error:
        error = None
    # get advancement from database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ADVANCEMENTS WHERE ID = ?", (advancement_id,))
        advancement = cursor.fetchone()
        if not advancement:
            error = "Advancement not found."
    except sqlite3.Error as e:
        error = e
    
    conn.close()
    
    # get all image names from static/images/item and static/images/block directories
    item_images = os.listdir("static/images/items")
    block_images = os.listdir("static/images/blocks")

    image_type = advancement["image"].split("/")[0] if advancement else None
    image_name = advancement["image"].split("/")[1] if advancement else None

    print(f"Advancement ID: {advancement_id}, Image Type: {image_type}, Image Name: {image_name}")

    return render_template("admin/edit-advancement.html", advancement=advancement, error=error, image_type=image_type, image_name=image_name, item_images=item_images, block_images=block_images)


@app.route("/admin/assets/upload", methods=["POST"])
def upload_asset():
    error = None
    item_image = request.files.get("item-image")
    block_image = request.files.get("block-image")
    
    if not item_image and not block_image:
        error = "No files uploaded."
    
    if item_image:
        item_image.save(os.path.join("static/images/items", item_image.filename))
    
    if block_image:
        block_image.save(os.path.join("static/images/blocks", block_image.filename))
    
    if error:
        return redirect(f"/admin/assets?error={error}")
    return redirect("/admin/assets")


@app.route("/admin/advancements/edit/<int:advancement_id>/submit", methods=["POST"])
def edit_advancement_submit(advancement_id):
    error = None

    name = request.form.get("name")
    description = request.form.get("description")
    item_image = request.form.get("item-image-name")
    block_image = request.form.get("block-image-name")
    image = "items/" + item_image if item_image else "blocks/" + block_image
    if not name or not description or not image:
        error = f"/admin/advancements/edit/{advancement_id}?error=All fields are required."
    else:
        # Update advancement in database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE ADVANCEMENTS SET name = ?, description = ?, image = ? WHERE ID = ?",
                (name, description, image, advancement_id)
            )
            conn.commit()
        except sqlite3.Error as e:
            error = f"/admin/advancements/edit/{advancement_id}?error=Error updating advancement: {e}"
        finally:
            conn.close()
    if error:
        return redirect(f"/admin/advancements/edit/{advancement_id}?error={error}")
    return redirect(f"/admin/advancements/list")


@app.route("/admin/advancements/delete/<int:advancement_id>", methods=["POST"])
def delete_advancement(advancement_id):
    # Delete advancement from database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ADVANCEMENTS WHERE ID = ?", (advancement_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.close()
        return redirect(f"/admin/advancements/list?error=Error deleting advancement: {e}")
    return redirect(f"/admin/advancements/list")


@app.route("/admin/assets/delete/<string:asset_type>/<string:asset_name>", methods=["POST"])
def delete_asset(asset_type, asset_name):
    # Delete asset from filesystem
    path = os.path.join("static/images/", asset_type, asset_name)
    try:
        if os.path.exists(path):
            os.remove(path)
        else:
            return redirect(f"/admin/assets?error=Asset not found: {asset_name}")
    except Exception as e:
        return redirect(f"/admin/assets?error=Error deleting asset: {e}")

    return redirect("/admin/assets")


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


# ...existing code...
@app.route("/admin/advancements/layout-submit", methods=["POST"])
def advancements_layout_submit_action():
    action = request.form.get("action")

    with open("data/layout.json", "r") as f:
        layout_data = json.load(f)
    
    max_x = int(max(layout_data.keys(), key=int)) if layout_data else 0
    min_x = int(min(layout_data.keys(), key=int)) if layout_data else 0
    
    max_y = int(max(max(layout_data[x].keys(), key=int) for x in layout_data)) if layout_data else 0
    min_y = int(min(min(layout_data[x].keys(), key=int) for x in layout_data)) if layout_data else 0

    if action == "add-row-top":
        # Add a new row at the top (decrease y values)
        for x in layout_data:
            layout_data[x][str(min_y - 1)] = {"id": "NONE", "bg": "NONE"}
    elif action == "add-row-bottom":
        # Add a new row at the bottom (increase y values)
        for x in layout_data:
            layout_data[x][str(max_y + 1)] = {"id": "NONE", "bg": "NONE"}
    elif action == "add-column-left":
        # Add a new column to the left (decrease x values)
        new_x = str(min_x - 1)
        layout_data[new_x] = {str(y): {"id": "NONE", "bg": "NONE"} for y in range(min_y, max_y + 1)}
    elif action == "add-column-right":
        # Add a new column to the right (increase x values)
        new_x = str(max_x + 1)
        layout_data[new_x] = {str(y): {"id": "NONE", "bg": "NONE"} for y in range(min_y, max_y + 1)}
    elif action == "remove-row-top":
        # Remove the top row (remove smallest y)
        for x in layout_data:
            if str(min_y) in layout_data[x]:
                del layout_data[x][str(min_y)]
    elif action == "remove-row-bottom":
        # Remove the bottom row (remove largest y)
        for x in layout_data:
            if str(max_y) in layout_data[x]:
                del layout_data[x][str(max_y)]
    elif action == "remove-column-left":
        # Remove the leftmost column (remove smallest x)
        if str(min_x) in layout_data:
            del layout_data[str(min_x)]
    elif action == "remove-column-right":
        # Remove the rightmost column (remove largest x)
        if str(max_x) in layout_data:
            del layout_data[str(max_x)]
    elif action == "download":
        # Download the layout as a JSON file
        return redirect("/admin/advancements/layout/download")

    # order the layout data by x and y
    layout_data = {k: dict(sorted(v.items(), key=lambda item: int(item[0]))) for k, v in sorted(layout_data.items(), key=lambda item: int(item[0]))}

    # Save the updated layout back to the file
    with open("data/layout.json", "w") as f:
        json.dump(layout_data, f, indent=4)

    return redirect("/admin/advancements/layout")
# ...existing code...


@app.route("/admin/advancements/layout/download")
def advancements_layout_download():
    # Load the layout data
    with open("data/layout.json", "r") as f:
        layout_data = json.load(f)

    # Create a JSON response
    response = app.response_class(
        response=json.dumps(layout_data, indent=4),
        status=200,
        mimetype='application/json'
    )
    response.headers["Content-Disposition"] = "attachment; filename=layout.json"
    
    return response


@app.route("/admin/advancements/layout-submit/<string:x>/<string:y>", methods=["POST"])
def advancements_layout_submit(x, y):
    # Get the layout data from the form
    bg = request.form.get("background")
    id = request.form.get("advancement")

    # Load the existing layout
    with open("data/layout.json", "r") as f:
        layout_data = json.load(f)

    # Update the layout data
    if x not in layout_data:
        layout_data[x] = {}
    layout_data[x][y] = {"id": id, "bg": bg}

    # Save the updated layout back to the file
    with open("data/layout.json", "w") as f:
        json.dump(layout_data, f, indent=4)

    return redirect("/admin/advancements/layout")


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
    app.run(debug=True, use_reloader=True, host="0.0.0.0", port=5001)

# /main.py