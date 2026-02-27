import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ------------------ APP CONFIG ------------------

app = Flask(__name__, static_folder='static', template_folder='templates')

app.secret_key = "supersecretkey"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'ecommerce.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')


db.init_app(app)

# Import models AFTER db init
from models import Product, User

with app.app_context():
    db.create_all()



# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

    # NEW FIELDS
    image_width = db.Column(db.Integer, default=250)
    image_height = db.Column(db.Integer, default=250)
    card_size = db.Column(db.String(20), default="medium")  # small / medium / large

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    quantity = db.Column(db.Integer)

# ------------------ ROUTES ------------------

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return redirect('/register')

        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()

        flash("Registration Successful")
        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            return redirect('/')
        else:
            flash("Invalid Credentials")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('is_admin'):
        flash("Admin access required")
        return redirect('/')

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])

        image = request.files['image']

        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_width = int(request.form.get('image_width', 250))
            image_height = int(request.form.get('image_height', 250))
            card_size = request.form.get('card_size', 'medium')
           
            product = Product(
                name=name,
                description=description,
                price=price,
                stock=stock,
                image=filename,
                image_width=image_width,
                image_height=image_height,
                card_size=card_size
            )

            db.session.add(product)
            db.session.commit()

            flash("Product Added Successfully")
            return redirect('/')

    return render_template('add_product.html')

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    existing = Cart.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()

    if existing:
        existing.quantity += 1
    else:
        cart_item = Cart(
            user_id=session['user_id'],
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart_item)

    db.session.commit()
    return redirect('/cart')

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    quantity = int(request.form['quantity'])

    cart_item = Cart.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity = quantity
        db.session.commit()

    return redirect('/cart')


@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    cart_item = Cart.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()

    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()

    return redirect('/cart')


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect('/login')

    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    products = []
    total = 0

    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            products.append((product, item.quantity))
            total += product.price * item.quantity

    return render_template('cart.html', products=products, total=total)

# -------------------ADMIN CREATION --------------

def create_admin():
    admin_email = "admin@startup.com"
    admin_password = "admin123"   # change later in production

    existing_admin = User.query.filter_by(email=admin_email).first()

    if not existing_admin:
        hashed_password = generate_password_hash(admin_password)

        admin = User(
            name="Super Admin",
            email=admin_email,
            password=hashed_password,
            is_admin=True
        )

        db.session.add(admin)
        db.session.commit()
        print("✅ Admin account created successfully!")
    else:
        print("ℹ Admin already exists.")


# ------------------ RUN APP ------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()   # 👈 ADD THIS LINE
    app.run(debug=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))