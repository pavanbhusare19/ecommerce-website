
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
import re

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "ecommerce.db")

SAMPLE_PRODUCTS = [
    ("Wireless Headphones", "Electronics", 1499,
     "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600", 20),
    ("Smart Watch", "Electronics", 2299,
     "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600", 15),
    ("Bluetooth Speaker", "Electronics", 999,
     "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600", 18),
    ("Running Shoes", "Fashion", 1799,
     "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600", 20),
    ("Classic T-Shirt", "Fashion", 599,
     "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600", 30),
    ("Backpack", "Fashion", 1199,
     "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600", 12),
    ("Table Lamp", "Home", 799,
     "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600", 15),
    ("Coffee Mug", "Home", 299,
     "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=600", 40),
    ("Sunglasses", "Accessories", 699,
     "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600", 20),
    ("Wrist Watch", "Accessories", 1599,
     "https://images.unsplash.com/photo-1524592094714-0f0654e20314?w=600", 10),
    ("Leather Wallet", "Accessories", 499,
     "https://images.unsplash.com/photo-1627123424574-724758594e93?w=600", 25),
    ("Desk Organizer", "Home", 449,
     "https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?w=600", 14)
]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL,
                image TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
        """)

        count = db.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if count == 0:
            db.executemany("""
                INSERT INTO products
                (name, category, price, image, stock)
                VALUES (?, ?, ?, ?, ?)
            """, SAMPLE_PRODUCTS)

    print("Database initialized successfully!")


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    if filename in {
        "app.py", "ecommerce.db", "ecommerce.db-journal"
    }:
        return jsonify({"error": "Not found"}), 404

    return send_from_directory(BASE_DIR, filename)


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "database": "SQLite"
    })


@app.route("/api/products")
def get_products():
    with get_db() as db:
        products = db.execute("""
            SELECT id, name, category, price, image, stock
            FROM products
            WHERE stock > 0
            ORDER BY id
        """).fetchall()

    return jsonify([dict(product) for product in products])


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request data"}), 400

    name = data.get("customer_name")
    email = data.get("email")
    phone = data.get("phone")
    address = data.get("address")
    items = data.get("items")

    if not all(isinstance(value, str) for value in
               [name, email, phone, address]):
        return jsonify({"error": "Please enter all customer details"}), 400

    name = name.strip()
    email = email.strip()
    phone = phone.strip()
    address = address.strip()

    if not name or len(name) > 100:
        return jsonify({"error": "Enter a valid name"}), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 150:
        return jsonify({"error": "Enter a valid email address"}), 400

    if not re.fullmatch(r"[0-9+\-\s()]{10,20}", phone):
        return jsonify({"error": "Enter a valid phone number"}), 400

    if not address or len(address) > 500:
        return jsonify({"error": "Enter a valid delivery address"}), 400

    if not isinstance(items, list) or not items or len(items) > 30:
        return jsonify({"error": "Your cart is empty or invalid"}), 400

    quantities = {}

    for item in items:
        if not isinstance(item, dict):
            return jsonify({"error": "Invalid cart item"}), 400

        product_id = item.get("product_id")
        quantity = item.get("quantity")

        if (type(product_id) is not int or
                type(quantity) is not int or
                product_id <= 0 or quantity < 1 or quantity > 20):
            return jsonify({"error": "Invalid product or quantity"}), 400

        if product_id in quantities:
            return jsonify({"error": "Duplicate cart item"}), 400

        quantities[product_id] = quantity

    try:
        with get_db() as db:
            total = 0
            order_products = []

            # Verify product prices and stock using database records
            for product_id, quantity in quantities.items():
                product = db.execute(
                    "SELECT * FROM products WHERE id = ?",
                    (product_id,)
                ).fetchone()

                if product is None:
                    return jsonify({"error": "Product not found"}), 400

                if product["stock"] < quantity:
                    return jsonify({
                        "error": f"Not enough stock for {product['name']}"
                    }), 400

                total += product["price"] * quantity
                order_products.append((product, quantity))

            cursor = db.execute("""
                INSERT INTO orders
                (customer_name, email, phone, address, total)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, phone, address, total))

            order_id = cursor.lastrowid

            for product, quantity in order_products:
                db.execute("""
                    INSERT INTO order_items
                    (order_id, product_id, product_name, price, quantity)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    order_id,
                    product["id"],
                    product["name"],
                    product["price"],
                    quantity
                ))

                db.execute("""
                    UPDATE products
                    SET stock = stock - ?
                    WHERE id = ?
                """, (quantity, product["id"]))

        return jsonify({
            "message": "Order placed successfully",
            "order_id": order_id,
            "total": total
        }), 201

    except sqlite3.Error:
        app.logger.exception("Order database error")
        return jsonify({"error": "Unable to save order"}), 500


if __name__ == "__main__":
    initialize_database()
    print("ShopEase backend starting...")
    app.run(host="127.0.0.1", port=5000, debug=False)
