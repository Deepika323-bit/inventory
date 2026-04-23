from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime

app = Flask(__name__)
app.secret_key = "stationery_secret"

# ---------------- DATABASE ---------------- #

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Deepika%40password26@localhost/stationery_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    contact_person = db.Column(db.String(15))
    email = db.Column(db.String(120))
    category = db.Column(db.String(100))


class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    product = db.Column(db.String(100))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    total = db.Column(db.Float)
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplier = db.relationship('Supplier', backref='orders')


class SalesOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50))
    customer = db.Column(db.String(100))
    product = db.Column(db.String(100))
    total = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.drop_all()
    db.create_all()

# ---------------- HOME ---------------- #

@app.route('/')
def home():
    return render_template("index.html")

# ---------------- REGISTER ---------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        # Accept JSON or Form Data
        if request.is_json:
            data = request.get_json()
            shop_name = data.get('shopName')
            email = data.get('email')
            password = data.get('password')
        else:
            shop_name = request.form.get('shopName')
            email = request.form.get('email')
            password = request.form.get('password')

        # Validation
        if not shop_name or not email or not password:
            return jsonify({"message": "All fields are required"}), 400

        hashed_pw = generate_password_hash(password)

        new_user = User(
            shop_name=shop_name,
            email=email,
            password=hashed_pw
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            return jsonify({"message": "Shop registered successfully!"}), 201

        except IntegrityError:
            db.session.rollback()
            return jsonify({"message": "Email already exists!"}), 400

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": str(e)}), 500

    return render_template('register.html')


# ---------------- SETUP ---------------- #
@app.route('/setup')
def setup():
    return render_template('setup.html')
# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')

        if not email or not password:
            return jsonify({"message": "All fields required"}), 400

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            return jsonify({
                "message": "Login Successful",
                "redirect": "/dashboard"
            }), 200
        else:
            return jsonify({"message": "Invalid email or password"}), 401

    return render_template('login.html')


# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard')
def dashboard():

    stock_value = db.session.query(db.func.sum(PurchaseOrder.total)).scalar() or 0
    total_sales = db.session.query(db.func.sum(SalesOrder.total)).scalar() or 0
    low_stock = PurchaseOrder.query.filter(PurchaseOrder.quantity < 10).count()

    stats = {
        "stock_value": stock_value,
        "total_sales": total_sales,
        "low_stock_items": low_stock
    }

    return render_template("dashboard.html", stats=stats)

# ---------------- SUPPLIERS ---------------- #

@app.route('/suppliers')
def suppliers():

    suppliers = Supplier.query.all()
    return render_template("suppliers.html", suppliers=suppliers)


@app.route('/add_supplier', methods=['POST'])
def add_supplier():

    supplier = Supplier(
        id=request.form.get('id'),
        name=request.form.get('name'),
        contact_person=request.form.get('contact'),
        email=request.form.get('email'),
        category=request.form.get('category')
    )

    db.session.add(supplier)
    db.session.commit()

    return redirect('/suppliers')

# ---------------- PURCHASE ---------------- #

@app.route('/purchase')
def purchase():

    orders = PurchaseOrder.query.all()
    suppliers = Supplier.query.all()

    return render_template("purchase.html", orders=orders, suppliers=suppliers)


@app.route('/add_purchase', methods=['POST'])
def add_purchase():

    supplier_id = request.form.get('supplier_id')
    product = request.form.get('product')
    quantity = int(request.form.get('quantity'))
    price = float(request.form.get('price'))

    order = PurchaseOrder(
        supplier_id=supplier_id,
        product=product,
        quantity=quantity,
        price=price,
        total=quantity*price
    )

    db.session.add(order)
    db.session.commit()

    return redirect('/purchase')


@app.route('/update_purchase/<int:id>', methods=['POST'])
def update_purchase(id):

    order = PurchaseOrder.query.get_or_404(id)
    order.status = request.form.get('status')

    db.session.commit()

    return redirect('/purchase')


@app.route('/delete_purchase/<int:id>')
def delete_purchase(id):

    order = PurchaseOrder.query.get_or_404(id)

    db.session.delete(order)
    db.session.commit()

    return redirect('/purchase')

# ---------------- SALES ---------------- #


@app.route('/sales')
def sales():
    orders = SalesOrder.query.all()
    print(orders)
    return render_template("sales.html", orders=orders)

@app.route('/add_sale', methods=['POST'])
def add_sale():

    order_no = request.form.get('order_no')
    customer = request.form.get('customer')
    product = request.form.get('product')
    total = request.form.get('total')

    sale = SalesOrder(
        order_no=order_no,
        customer=customer,
        product=product,
        total=total
    )

    db.session.add(sale)
    db.session.commit()

    return redirect('/sales')

# ---------------- PROFILE ---------------- #

@app.route('/profile')
def profile_view():

    user_data = {
        "shop_name": "Blue Ink Stationery Hub",
        "owner_name": "Arjun Patel",
        "email": "contact@blueinkhub.com",
        "phone": "+919876543210",
        "address": "Solapur, Maharashtra",
        "joined": "January 2026"
    }

    return render_template('profile.html', user=user_data)

# ---------------- SETTINGS ---------------- #

@app.route('/settings')
def settings():

    config = {
        "tax_percentage": 18,
        "low_stock_limit": 10,
        "currency": "INR",
        "email_notifications": True
    }

    return render_template('settings.html', config=config)

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)