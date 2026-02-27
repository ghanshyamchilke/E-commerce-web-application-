import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "supersecretkey"

# Database (Render compatible)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/ecommerce.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload folder inside static (VERY IMPORTANT)
app.config["UPLOAD_FOLDER"] = "static/uploads"

db = SQLAlchemy(app)

# Create upload folder if not exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ------------------ MODELS ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    image = db.Column(db.String(200))
    stock = db.Column(db.Integer)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    quantity = db.Column(db.Integer)


# ------------------ CREATE TABLES ------------------

with app.app_context():
    db.create_all()


# ------------------ ROUTES ------------------

@app.route("/")
def index():
    products = Product.query.all()
    return render_template("index.html", products=products)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return redirect("/register")

        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        flash("Registration Successful")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["is_admin"] = user.is_admin
            return redirect("/")
        else:
            flash("Invalid Credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if not session.get("is_admin"):
        flash("Admin access required")
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])

        image = request.files["image"]

        filename = None
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            image=filename
        )

        db.session.add(product)
        db.session.commit()

        flash("Product Added Successfully")
        return redirect("/")

    return render_template("add_product.html")


@app.route("/product/<int:id>")
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template("product_detail.html", product=product)


@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect("/login")

    cart_items = Cart.query.filter_by(user_id=session["user_id"]).all()
    products = []
    total = 0

    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            products.append((product, item.quantity))
            total += product.price * item.quantity

    return render_template("cart.html", products=products, total=total)


@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "user_id" not in session:
        return redirect("/login")

    existing = Cart.query.filter_by(
        user_id=session["user_id"],
        product_id=product_id
    ).first()

    if existing:
        existing.quantity += 1
    else:
        cart_item = Cart(
            user_id=session["user_id"],
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart_item)

    db.session.commit()
    return redirect("/cart")


