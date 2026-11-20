
const productGrid = document.getElementById("productGrid");
const searchInput = document.getElementById("searchInput");
const cartButton = document.getElementById("cartButton");
const cartDrawer = document.getElementById("cartDrawer");
const cartOverlay = document.getElementById("cartOverlay");
const cartItems = document.getElementById("cartItems");
const cartCount = document.getElementById("cartCount");
const cartTotal = document.getElementById("cartTotal");

let products = [];
let cart = [];
let activeCategory = "All";

document.getElementById("currentYear").textContent =
    new Date().getFullYear();

function formatPrice(price) {
    return "₹" + Number(price).toLocaleString("en-IN");
}

// Load products from Flask backend
async function loadProducts() {
    try {
        const response = await fetch("/api/products");

        if (!response.ok) {
            throw new Error("Unable to load products");
        }

        products = await response.json();
        renderProducts();
    } catch (error) {
        productGrid.innerHTML =
            '<p class="empty-products">Could not load products. Please refresh the page.</p>';
        console.error(error);
    }
}

// Display products
function renderProducts() {
    const searchTerm = searchInput.value.trim().toLowerCase();

    const filtered = products.filter(product => {
        const matchesCategory =
            activeCategory === "All" ||
            product.category === activeCategory;

        const matchesSearch =
            product.name.toLowerCase().includes(searchTerm) ||
            product.category.toLowerCase().includes(searchTerm);

        return matchesCategory && matchesSearch;
    });

    if (filtered.length === 0) {
        productGrid.innerHTML =
            '<p class="empty-products">No products found.</p>';
        return;
    }

    productGrid.innerHTML = filtered.map(product => `
        <article class="product-card">
            <img src="${escapeHTML(product.image)}"
                 alt="${escapeHTML(product.name)}"
                 onerror="this.src='https://placehold.co/400x300?text=Product'">
            <div class="product-info">
                <span class="product-category">${escapeHTML(product.category)}</span>
                <h3>${escapeHTML(product.name)}</h3>
                <p class="product-price">${formatPrice(product.price)}</p>
                <button class="add-button" data-add="${product.id}">
                    Add to Cart +
                </button>
            </div>
        </article>
    `).join("");
}

// Escape text before inserting API data into HTML
function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}

// Category filters
document.getElementById("categoryFilters").addEventListener("click", event => {
    const button = event.target.closest("[data-category]");

    if (!button) return;

    activeCategory = button.dataset.category;

    document.querySelectorAll(".filter").forEach(filter => {
        filter.classList.toggle("active", filter === button);
    });

    renderProducts();
});

// Search products
searchInput.addEventListener("input", renderProducts);

// Add product to cart
productGrid.addEventListener("click", event => {
    const button = event.target.closest("[data-add]");
    if (!button) return;

    const id = Number(button.dataset.add);
    const product = products.find(item => item.id === id);

    if (!product) return;

    const existing = cart.find(item => item.id === id);

    if (existing) {
        existing.quantity++;
    } else {
        cart.push({ ...product, quantity: 1 });
    }

    renderCart();
    button.textContent = "Added ✓";

    setTimeout(() => {
        button.textContent = "Add to Cart +";
    }, 800);
});

// Render shopping cart
function renderCart() {
    const totalItems = cart.reduce(
        (sum, item) => sum + item.quantity, 0
    );

    const totalPrice = cart.reduce(
        (sum, item) => sum + item.price * item.quantity, 0
    );

    cartCount.textContent = totalItems;
    cartTotal.textContent = formatPrice(totalPrice);

    if (cart.length === 0) {
        cartItems.innerHTML = "<p>Your cart is empty.</p>";
        return;
    }

    cartItems.innerHTML = cart.map(item => `
        <div class="cart-item">
            <img src="${escapeHTML(item.image)}" alt="">
            <div>
                <h4>${escapeHTML(item.name)}</h4>
                <p>${formatPrice(item.price)}</p>
                <div class="quantity-controls">
                    <button data-decrease="${item.id}">−</button>
                    <span>${item.quantity}</span>
                    <button data-increase="${item.id}">+</button>
                </div>
            </div>
            <button class="remove-item" data-remove="${item.id}">✕</button>
        </div>
    `).join("");
}

// Cart quantity and remove actions
cartItems.addEventListener("click", event => {
    const decrease = event.target.closest("[data-decrease]");
    const increase = event.target.closest("[data-increase]");
    const remove = event.target.closest("[data-remove]");

    if (decrease) {
        const item = cart.find(
            product => product.id === Number(decrease.dataset.decrease)
        );

        if (item) item.quantity--;

        cart = cart.filter(item => item.quantity > 0);
    }

    if (increase) {
        const item = cart.find(
            product => product.id === Number(increase.dataset.increase)
        );

        if (item) item.quantity++;
    }

    if (remove) {
        cart = cart.filter(
            item => item.id !== Number(remove.dataset.remove)
        );
    }

    renderCart();
});

// Open and close cart
function openCart() {
    cartDrawer.classList.add("open");
    cartOverlay.classList.add("show");
}

function closeCart() {
    cartDrawer.classList.remove("open");
    cartOverlay.classList.remove("show");
}

cartButton.addEventListener("click", openCart);
document.getElementById("closeCart").addEventListener("click", closeCart);
cartOverlay.addEventListener("click", closeCart);

// Checkout
const checkoutModal = document.getElementById("checkoutModal");

document.getElementById("checkoutButton").addEventListener("click", () => {
    if (cart.length === 0) {
        alert("Your cart is empty!");
        return;
    }

    checkoutModal.classList.add("show");
});

document.getElementById("closeCheckout").addEventListener("click", () => {
    checkoutModal.classList.remove("show");
});

document.getElementById("checkoutForm").addEventListener("submit", async event => {
    event.preventDefault();

    const form = event.currentTarget;
    const message = document.getElementById("checkoutMessage");
    const submitButton = form.querySelector('button[type="submit"]');

    const formData = new FormData(form);

    const orderData = {
        customer_name: formData.get("customer_name").trim(),
        email: formData.get("email").trim(),
        phone: formData.get("phone").trim(),
        address: formData.get("address").trim(),
        items: cart.map(item => ({
            product_id: item.id,
            quantity: item.quantity
        }))
    };

    if (!orderData.items.length) {
        message.textContent = "Your cart is empty.";
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Placing order...";

    try {
        const response = await fetch("/api/orders", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(orderData)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not place order");
        }

        message.textContent =
            `Order placed successfully! Order ID: ${result.order_id}`;

        cart = [];
        renderCart();
        form.reset();

        setTimeout(() => {
            checkoutModal.classList.remove("show");
            closeCart();
            message.textContent = "";
        }, 2500);

    } catch (error) {
        message.textContent = error.message;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Place Order";
    }
});

// Initial loading
renderCart();
loadProducts();
