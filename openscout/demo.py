"""Harbor Kiln — a demo shop with seeded bugs for OpenScout to find."""

from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

PRODUCTS = {
    "red-mug": {
        "slug": "red-mug",
        "name": "Red Mug",
        "price": 24,
        "blurb": "A wheel-thrown mug glazed in kiln red. Dishwasher safe.",
        "broken": False,
    },
    "indigo-bowl": {
        "slug": "indigo-bowl",
        "name": "Indigo Bowl",
        "price": 36,
        "blurb": "Deep cobalt glaze over a wide breakfast bowl.",
        "broken": False,
    },
    "broken-mug": {
        "slug": "broken-mug",
        "name": "Broken Mug",
        "price": 12,
        "blurb": "Seconds from the last firing. Handle may be loose.",
        "broken": True,
    },
}

app = FastAPI(title="Harbor Kiln demo shop")


def _cart(request: Request) -> list[str]:
    raw = request.cookies.get("kiln_cart", "[]")
    try:
        data = json.loads(raw)
        return [slug for slug in data if slug in PRODUCTS]
    except json.JSONDecodeError:
        return []


def _with_cart(response: HTMLResponse, cart: list[str]) -> HTMLResponse:
    response.set_cookie("kiln_cart", json.dumps(cart), httponly=False)
    return response


def page(title: str, body: str, cart_count: int = 0) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · Harbor Kiln</title>
  <style>
    :root {{ --ink:#2b2118; --paper:#f7f1e8; --clay:#c45c26; --line:#e6d8c6; --mute:#7a6a58; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:16px/1.5 "Iowan Old Style", Palatino, Georgia, serif; background:var(--paper); color:var(--ink); }}
    header {{ display:flex; justify-content:space-between; align-items:center; padding:18px 8vw; border-bottom:1px solid var(--line); }}
    a {{ color:var(--clay); text-decoration:none; }}
    nav a {{ margin-left:18px; color:var(--ink); }}
    main {{ padding:28px 8vw 80px; max-width:1100px; }}
    .hero {{ display:grid; grid-template-columns:1.2fr .8fr; gap:32px; align-items:center; }}
    .mark {{ width:100%; height:280px; border-radius:18px; background:
      radial-gradient(circle at 30% 30%, #e27d4a, #9a3412 62%, #5c2410); }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:20px; }}
    .card {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:18px; }}
    button, .btn {{ background:var(--clay); color:#fff; border:0; border-radius:999px; padding:10px 16px; cursor:pointer; font:inherit; }}
    button.ghost, a.ghost {{ background:transparent; color:var(--ink); border:1px solid var(--line); }}
    input, textarea {{ width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:10px; font:inherit; margin:6px 0 14px; }}
    .mute {{ color:var(--mute); }}
    .row {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    .flash {{ background:#ffe8d6; padding:10px 12px; border-radius:10px; }}
    .icon {{ width:36px; height:36px; border-radius:50%; border:1px solid var(--line); background:#fff; }}
    footer {{ padding:24px 8vw; color:var(--mute); border-top:1px solid var(--line); }}
    @media (max-width:800px) {{ .hero {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <a href="/" style="color:var(--ink); font-weight:700; letter-spacing:.04em;">HARBOR KILN</a>
    <nav>
      <a href="/shop">Shop</a>
      <a href="/cart">Cart ({cart_count})</a>
      <a href="/contact">Contact</a>
      <a href="/careers">Careers</a>
    </nav>
  </header>
  <main>{body}</main>
  <footer>Harbor Kiln demo shop — seeded with bugs for OpenScout.</footer>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    cart = _cart(request)
    body = """
    <section class="hero">
      <div>
        <p class="mute">Studio ceramics · Lisbon</p>
        <h1>Clay, fire, and a few intentional defects.</h1>
        <p>Harbor Kiln is a demo storefront. Most paths work. A few are broken on purpose so a testing agent has something real to catch.</p>
        <p><a class="btn" href="/shop">Shop</a></p>
      </div>
      <div>
        <img class="mark" src="data:image/svg+xml,{svg}" width="480" height="280" />
        <p class="mute">Firing no. 184</p>
      </div>
    </section>
    """.format(
        svg=quote(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 280">'
            '<rect fill="#c45c26" width="480" height="280"/>'
            '<circle cx="240" cy="140" r="90" fill="#f7f1e8" opacity=".35"/>'
            "</svg>"
        )
    )
    return HTMLResponse(page("Home", body, len(cart)))


@app.get("/shop", response_class=HTMLResponse)
def shop(request: Request) -> HTMLResponse:
    cart = _cart(request)
    cards = []
    for product in PRODUCTS.values():
        cards.append(
            f"""<article class="card">
              <h2><a href="/product/{product['slug']}">{product['name']}</a></h2>
              <p class="mute">${product['price']}</p>
              <p>{product['blurb']}</p>
            </article>"""
        )
    body = "<h1>Shop</h1><div class='grid'>" + "".join(cards) + "</div>"
    return HTMLResponse(page("Shop", body, len(cart)))


@app.get("/product/{slug}", response_class=HTMLResponse)
def product(slug: str, request: Request) -> HTMLResponse:
    item = PRODUCTS.get(slug)
    if not item:
        return HTMLResponse(page("Missing", "<h1>Not found</h1>"), status_code=404)
    cart = _cart(request)
    script = ""
    icon = ""
    if item["broken"]:
        script = """
        <script>
          console.error("Clay analytics: Failed to load product tracker");
          throw new Error("product tracker crashed");
        </script>
        """
        icon = '<p><button class="icon" type="button"></button></p>'
    body = f"""
    <p class="mute"><a href="/shop">Shop</a> / {item['name']}</p>
    <h1>{item['name']}</h1>
    <p>{item['blurb']}</p>
    <p><strong>${item['price']}</strong></p>
    <form method="post" action="/cart/add">
      <input type="hidden" name="slug" value="{item['slug']}" />
      <button type="submit">Add to cart</button>
    </form>
    {icon}
    {script}
    """
    return HTMLResponse(page(item["name"], body, len(cart)))


@app.post("/cart/add")
def add_to_cart(request: Request, slug: str = Form(...)) -> RedirectResponse:
    cart = _cart(request)
    if slug in PRODUCTS:
        cart.append(slug)
    response = RedirectResponse("/cart", status_code=303)
    response.set_cookie("kiln_cart", json.dumps(cart))
    return response


@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request) -> HTMLResponse:
    cart = _cart(request)
    if not cart:
        body = "<h1>Cart</h1><p>Your cart is empty.</p><p><a href='/shop'>Shop</a></p>"
        return HTMLResponse(page("Cart", body, 0))
    rows = []
    total = 0
    for slug in cart:
        item = PRODUCTS[slug]
        total += item["price"]
        rows.append(f"<div class='row'><span>{item['name']}</span><span>${item['price']}</span></div>")
    body = f"""
    <h1>Cart</h1>
    {''.join(rows)}
    <p><strong>Total ${total}</strong></p>
    <form method="post" action="/api/coupon" id="coupon-form">
      <label for="coupon">Coupon code</label>
      <input id="coupon" name="code" placeholder="SAVE50" />
      <button type="submit">Apply coupon</button>
      <p id="coupon-status" class="mute"></p>
    </form>
    <h2>Checkout</h2>
    <form method="post" action="/checkout">
      <label for="name">Full name</label>
      <input id="name" name="name" required />
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required />
      <div class="row">
        <button type="submit">Place order</button>
        <button type="button" id="express">Express checkout</button>
      </div>
    </form>
    <script>
      document.getElementById("coupon-form").addEventListener("submit", async (event) => {{
        event.preventDefault();
        const code = document.getElementById("coupon").value;
        const status = document.getElementById("coupon-status");
        const response = await fetch("/api/coupon", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ code }}),
        }});
        status.textContent = response.ok ? "Coupon applied" : "Coupon failed (" + response.status + ")";
      }});
      document.getElementById("express").addEventListener("click", () => {{
        throw new Error("Express pay SDK missing");
      }});
    </script>
    """
    return HTMLResponse(page("Cart", body, len(cart)))


@app.post("/api/coupon")
async def coupon(request: Request) -> JSONResponse:
    return JSONResponse({"ok": False, "error": "pricing service down"}, status_code=500)


@app.post("/checkout")
def checkout(request: Request, name: str = Form(...), email: str = Form(...)) -> HTMLResponse:
    body = f"""
    <h1>Order confirmed</h1>
    <p>Thanks, {name}. A firing note is on its way to {email}.</p>
    <p class="flash">Order HK-1842</p>
    """
    response = HTMLResponse(page("Order confirmed", body, 0))
    response.set_cookie("kiln_cart", "[]")
    return response


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request) -> HTMLResponse:
    cart = _cart(request)
    body = """
    <h1>Contact</h1>
    <form method="post" action="/contact">
      <label for="email">Email</label>
      <input id="email" name="email" />
      <label for="message">Message</label>
      <textarea id="message" name="message" rows="4"></textarea>
      <button type="submit">Send</button>
    </form>
    """
    return HTMLResponse(page("Contact", body, len(cart)))


@app.post("/contact", response_class=HTMLResponse)
def contact_submit(request: Request, email: str = Form(""), message: str = Form("")) -> HTMLResponse:
    cart = _cart(request)
    body = f"<h1>Message sent</h1><p class='mute'>We did not validate that '{email}' is an email.</p><p>{message}</p>"
    return HTMLResponse(page("Message sent", body, len(cart)))


@app.get("/careers", response_class=HTMLResponse)
def careers() -> HTMLResponse:
    return HTMLResponse(page("Careers", "<h1>This page is missing</h1><p>The kiln ate the jobs board.</p>"), status_code=404)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "shop": "harbor-kiln"}
