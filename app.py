"""
🌸 Petals Pavitra — Sacred flowers. A second life.
Streamlit e-commerce website (Streamlit + pandas + sqlite3). Keep the `assets/` folder next to this file.

RUN LOCALLY :  pip install streamlit pandas "qrcode[pil]"  &&  streamlit run app.py
RUN IN COLAB:  see the Colab cells given with this file.
DEPLOY      :  push app.py + requirements.txt (streamlit, pandas, qrcode[pil]) to GitHub,
               then deploy free on https://share.streamlit.io  (note: SQLite resets on redeploy).
Owner PIN   :  pavitra2026   |   Promo codes: PAVITRA10 (10% off), FLOWER50 (₹50 off)
"""
import io, os, time, base64, json, uuid, sqlite3, hashlib
from datetime import datetime
from urllib.parse import quote
import pandas as pd
import streamlit as st

def secret(k, default=None):
    """Read a value from Streamlit secrets (any upper/lower case, also inside [sections]) or the environment."""
    def find(d):
        for key in list(d.keys()):
            if str(key).lower() == k.lower(): return d[key]
        for key in list(d.keys()):
            if hasattr(d[key], "keys"):
                r = find(d[key])
                if r is not None: return r
        return None
    try:
        r = find(st.secrets)
        if r is not None: return r.strip() if isinstance(r, str) else r
    except Exception:
        pass
    return os.environ.get(k, os.environ.get(k.upper(), default))

def secret_names():
    try: return sorted(str(x) for x in st.secrets.keys())
    except Exception: return []

DB, BOX_EST = "petals_v2.db", 150                      # local fallback file; ₹150/box revenue estimate (PPT)
OWNER_PIN = str(secret("OWNER_PIN", "pavitra2026"))    # set OWNER_PIN in secrets for the live site!
DBURL = str(secret("postgresql://postgres.gaqwoevtdaxzbcfgcgvy:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres") or "").strip().strip("\"\'")   # Supabase link: put it in Streamlit SECRETS, never in this file!
PG = bool(DBURL)
PROMOS = {"PAVITRA10": ("pct", 10), "FLOWER50": ("flat", 50)}
STATUSES = ["Pending", "Shipped", "Delivered"]
UPI_ID = "6386907137@fam"
ASSETS = "assets"   # folder with the brand photos (hero.jpg, logo.jpg, ...)
CONTACT = {"email": "petals.pavitra@gmail.com", "phone": "+91 98765 43210",
           "address": "A-12, Green Valley, Indore (M.P.) · Anpara (U.P.) - 231225"}   # edit freely
COLOURS = {"Blush Pink + Sage Green": "box_pink.jpg", "Lavender + White": "box_lavender.jpg"}
SEED_IMG = {"Signature Flower Dhoop Cones": "cones.jpg", "Spiritual Gift Box & Hamper": "giftbox.jpg",
            "Festival Edition Dhoop Collection": "diya.jpg", "Eco-Friendly Incense Sticks": "petals.jpg"}
TEAM = [("Product Head", "Manufacturing & Product Development"), ("Creative Head", "Branding & Packaging"),
        ("Finance Head", "Costing & Pricing"), ("Marketing Head", "Social Media & Promotion"),
        ("Strategy & Research Head", "Market Research & PPT")]

HERE = os.path.dirname(os.path.abspath(__file__))
ALL_IMAGES = ["hero.jpg", "logo.jpg", "shapes.jpg", "hamper_info.jpg", "giftbox.jpg", "cones.jpg", "diya.jpg",
              "petals.jpg", "dhoop_card.jpg", "label.jpg", "box_pink.jpg", "box_lavender.jpg"]
try:
    from assets_data import IMAGES      # {filename: base64} — upload assets_data.py next to app.py
except Exception:
    IMAGES = {}

def img_b64(name):
    """Base64 of a bundled photo: from assets_data.py if present, else from the assets/ folder."""
    if not name: return None
    if name in IMAGES: return IMAGES[name]
    for base in (os.path.join(HERE, ASSETS), ASSETS):
        p = os.path.join(base, name)
        if os.path.isfile(p): return _b64(p)
    return None

@st.cache_data
def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def _embed(b64, width=None):
    raw = base64.b64decode(b64)
    if width: st.image(raw, width=width)
    else: st.image(raw)

def show(name, width=None):
    b = img_b64(name)
    if b: _embed(b, width)

def show_product(p, width=None):
    """Product photo: uploaded photo stored in the database, else the bundled asset."""
    if str(p.get("img_data") or ""): _embed(p["img_data"], width)
    else: show(p.get("img"), width)

def photo_b64(f):
    """Uploaded photo -> resized JPEG -> base64 text (stored in the database, survives restarts)."""
    if f is None: return ""
    from PIL import Image
    im = Image.open(f).convert("RGB"); im.thumbnail((800, 800))
    b = io.BytesIO(); im.save(b, "JPEG", quality=80)
    return base64.b64encode(b.getvalue()).decode()

# ───────────────────────── Database ─────────────────────────
if PG:
    import psycopg2

@st.cache_resource
def _pg():
    c = psycopg2.connect(DBURL, connect_timeout=10)
    c.autocommit = True
    return c

def _exec(sql, args=(), fetch=False):
    if PG:
        sql = sql.replace("?", "%s")
        for attempt in (0, 1):
            try:
                with _pg().cursor() as cur:
                    cur.execute(sql, args)
                    if fetch:
                        return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
                    return None
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                if attempt: raise
                _pg.clear()          # connection dropped -> reconnect and retry once
    else:
        with sqlite3.connect(DB) as c:
            cur = c.execute(sql, args)
            if fetch:
                return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])

def run(sql, args=()):
    _exec(sql, args)

def table(sql, args=()):
    return _exec(sql, args, True)

UPSERT = "INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v"

def init_db():
    pk = "SERIAL PRIMARY KEY" if PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    run("CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, name TEXT, pw TEXT)")
    run(f"""CREATE TABLE IF NOT EXISTS products(id {pk}, name TEXT, descr TEXT, price DOUBLE PRECISION,
           emoji TEXT, img TEXT DEFAULT '', img_data TEXT DEFAULT '', avail INTEGER DEFAULT 1)""")
    run("""CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, email TEXT, name TEXT, phone TEXT, address TEXT,
           items TEXT, subtotal DOUBLE PRECISION, discount DOUBLE PRECISION, shipping DOUBLE PRECISION DEFAULT 0,
           total DOUBLE PRECISION, method TEXT, status TEXT, created TEXT, ts DOUBLE PRECISION,
           pay_status TEXT, utr TEXT)""")
    run("CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT)")
    for k, v in [("upi_id", secret("UPI_ID", UPI_ID)), ("payee", "Petals Pavitra"),
                 ("ship_fee", "49"), ("free_above", "499")]:
        run("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING", (k, str(v)))
    if table("SELECT COUNT(*) n FROM products").n[0] == 0:
        for row in [("Signature Flower Dhoop Cones", "Made from recycled temple flowers with natural fragrance.", 150, "🌺"),
                    ("Spiritual Gift Box & Hamper", "Premium festive packaging — a thoughtful sacred gift.", 450, "🎁"),
                    ("Festival Edition Dhoop Collection", "Diwali / Navratri special fragrances.", 299, "🪔"),
                    ("Eco-Friendly Incense Sticks", "Hand-rolled from sacred petals.", 120, "🌸")]:
            run("INSERT INTO products(name,descr,price,emoji) VALUES(?,?,?,?)", row)

def notify(subject, body, to):
    """Optional e-mail alert (needs SMTP_USER + SMTP_PASS in secrets). Never blocks an order."""
    u, p = secret("SMTP_USER"), secret("SMTP_PASS")
    if not (u and p and to): return
    try:
        import smtplib
        from email.message import EmailMessage
        m = EmailMessage(); m["Subject"], m["From"], m["To"] = subject, f"Petals Pavitra <{u}>", to
        m.set_content(body)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as sm:
            sm.login(u, p); sm.send_message(m)
    except Exception:
        pass

def link_images():
    for nm, fn in SEED_IMG.items():
        run("UPDATE products SET img=? WHERE name=? AND (img IS NULL OR img='')", (fn, nm))

def get_setting(k):
    r = table("SELECT v FROM settings WHERE k=?", (k,))
    return r.v[0] if not r.empty else ""

def hash_pw(p, email):
    return hashlib.pbkdf2_hmac("sha256", p.encode(), (email.strip().lower() + "petals-pavitra").encode(), 100_000).hex()
def _redact(msg):
    from urllib.parse import urlparse, unquote
    try:
        pw = urlparse(DBURL).password
        for x in filter(None, [DBURL, pw, unquote(pw or "")]): msg = msg.replace(x, "***")
    except Exception:
        pass
    return msg

if PG:   # fail loudly instead of silently saving orders in a temporary database
    try:
        if not DBURL.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must start with postgresql://")
        _pg()
    except Exception as e:
        _pg.clear()
        st.error("⚠️ The store cannot connect to its database right now, so orders are paused.")
        st.caption("Owner: open Streamlit → Manage app → Settings → Secrets and check DATABASE_URL. Use the Supabase "
                   "*Session pooler* link (user looks like postgres.abcd…), with your real password and no [ ] brackets.")
        if isinstance(e, ValueError): st.code(str(e))
        else: st.code(_redact((str(e).strip().splitlines() or [type(e).__name__])[0])[:220])
        st.stop()

init_db()
link_images()

# ───────────────────────── Session state ─────────────────────────
for k, v in {"role": None, "user": None, "cart": {}, "promo": "", "last_order": None}.items():
    st.session_state.setdefault(k, v)
S = st.session_state

def totals():
    """Return (cart rows, subtotal, discount, total) for the current cart + promo."""
    rows, sub = [], 0.0
    for key, qty in S.cart.items():
        pid, _, var = str(key).partition("|")
        p = table("SELECT * FROM products WHERE id=?", (int(pid),))
        if p.empty or qty <= 0:
            continue
        p = p.iloc[0]
        rows.append({"key": str(key), "id": int(pid), "qty": int(qty), "price": float(p["price"]),
                     "name": p["name"] + (f" ({var})" if var else "")})
        sub += p["price"] * qty
    kind, val = PROMOS.get(S.promo, (None, 0))
    disc = sub * val / 100 if kind == "pct" else (min(val, sub) if kind == "flat" else 0)
    fee, free = float(get_setting("ship_fee") or 0), float(get_setting("free_above") or 0)
    ship = 0.0 if (not rows or sub >= free) else fee
    return rows, sub, disc, ship, sub - disc + ship

def invoice(o):
    items = json.loads(o["items"])
    lines = "".join(f"<tr><td>{i['name']}</td><td>{i['qty']}</td><td>₹{i['price']:.0f}</td>"
                    f"<td>₹{i['price']*i['qty']:.0f}</td></tr>" for i in items)
    st.markdown(f"""<div class='invoice'><h3>🧾 Invoice — {o['id']}</h3>
    <p>{o['created']} · <b>{o['status']}</b> · {o['method']} · Payment: <b>{o['pay_status']}</b></p>
    <p><b>{o['name']}</b> · {o['phone']}<br>{o['address']}</p>
    <table width='100%'><tr><th align=left>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>{lines}</table>
    <hr>Subtotal ₹{o['subtotal']:.0f} · Discount −₹{o['discount']:.0f} · Shipping ₹{o['shipping']:.0f} · <b>Total ₹{o['total']:.0f}</b></div>""",
                unsafe_allow_html=True)

STORY = ("<div class='story'><b>🌿 Our Story — Waste to Fragrance.</b><br>Every day, tonnes of flowers offered at "
         "temples end up in rivers and landfills. Petals Pavitra collects this sacred floral waste, dries and "
         "transforms it into dhoop cones and incense — closing the loop: <i>temple → petals → fragrance → home.</i> "
         "Sacred flowers. A second life.</div>")

# ───────────────────────── Login / Signup ─────────────────────────
def login_page():
    show("hero.jpg")
    st.caption("Sacred flowers. A second life.")
    st.markdown(STORY, unsafe_allow_html=True)
    st.write("")
    role = st.radio("I am a…", ["Customer", "Owner / Admin"], horizontal=True)
    if role == "Customer":
        t1, t2 = st.tabs(["Login", "Sign up"])
        with t1:
            with st.form("login"):
                e, p = st.text_input("Email"), st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    u = table("SELECT * FROM users WHERE email=? AND pw=?", (e.strip().lower(), hash_pw(p, e)))
                    if u.empty:
                        st.error("Invalid email or password.")
                    else:
                        S.role, S.user = "customer", {"email": u.email[0], "name": u.name[0]}
                        st.rerun()
        with t2:
            with st.form("signup"):
                n, e = st.text_input("Full name"), st.text_input("Email ")
                p = st.text_input("Password (min 6 chars)", type="password")
                if st.form_submit_button("Create account"):
                    e = e.strip().lower()
                    if not n or "@" not in e or len(p) < 6:
                        st.error("Enter a name, valid email and a 6+ character password.")
                    elif not table("SELECT 1 FROM users WHERE email=?", (e,)).empty:
                        st.error("Email already registered.")
                    else:
                        run("INSERT INTO users VALUES(?,?,?)", (e, n, hash_pw(p, e)))
                        S.role, S.user = "customer", {"email": e, "name": n}
                        st.rerun()
    else:
        with st.form("owner"):
            pin = st.text_input("Owner PIN", type="password")
            if st.form_submit_button("Enter Owner Portal"):
                if pin == OWNER_PIN:
                    S.role, S.user = "owner", {"email": "owner", "name": "Owner"}
                    st.rerun()
                else:
                    st.error("Wrong PIN.")

# ───────────────────────── Customer pages ─────────────────────────
def page_home():
    show("hero.jpg")
    st.header("Sacred flowers. A second life.")
    st.write("Petals Pavitra turns temple flower waste into **eco-friendly dhoop and spiritual products** — "
             "traditional in spirit, modern in design.")
    for col, (ic, t) in zip(st.columns(4), [("♻️", "Reuse Flower Waste"), ("🌿", "Eco-Friendly Product"),
                                            ("🪔", "Traditional Meets Modern"), ("🎁", "Perfect for Gifting")]):
        col.markdown(f"<div class='card' style='min-height:110px'><div class='emoji' style='font-size:34px'>{ic}</div>"
                     f"<b>{t}</b></div>", unsafe_allow_html=True)
    st.subheader("🌸 Our Dhoop Shapes")
    show("shapes.jpg")
    st.subheader("🎁 Gift Hamper — Sacred Bloom Collection")
    show("hamper_info.jpg")
    st.markdown(STORY, unsafe_allow_html=True)
    st.info("Use promo **PAVITRA10** (10% off) or **FLOWER50** (₹50 off) at checkout. Open **🛍️ Shop** in the sidebar to order.")

def page_shop():
    st.title("🛍️ Shop")
    prods = table("SELECT * FROM products ORDER BY id")
    cols = st.columns(2)
    for i, p in prods.iterrows():
        with cols[i % 2], st.container(border=True):
            show_product(p)
            st.markdown(f"#### {p.emoji} {p['name']}")
            st.write(p.descr)
            st.markdown(f"<span class='price'>₹{p.price:.0f}</span>", unsafe_allow_html=True)
            if not p.avail:
                st.warning("Currently out of stock"); continue
            var = ""
            if "Gift Box" in p["name"]:
                var = st.radio("Box colour", list(COLOURS), key=f"v{p.id}", horizontal=True)
                show(COLOURS[var])
            n = st.number_input("Qty", 1, 20, 1, key=f"q{p.id}")
            if st.button("Add to cart 🛒", key=f"a{p.id}"):
                k = f"{int(p.id)}|{var}" if var else str(int(p.id))
                S.cart[k] = S.cart.get(k, 0) + n
                st.toast(f"Added {p['name']}")
    with st.expander("🌿 Read Our Story"):
        st.markdown(STORY, unsafe_allow_html=True)
    with st.expander("📋 Ingredients, how to use & caution"):
        show("label.jpg")

def page_cart():
    st.title("🛒 Your Cart")
    rows, sub, disc, ship, total = totals()
    if not rows:
        st.info("Your cart is empty."); return
    for r in rows:
        c1, c2, c3 = st.columns([4, 2, 2])
        c1.write(f"**{r['name']}**  ·  ₹{r['price']:.0f}")
        S.cart[r["key"]] = c2.number_input("Qty (0 = remove)", 0, 50, r["qty"], key=f"cq{r['key']}")
        c3.write(f"₹{r['price'] * S.cart[r['key']]:.0f}")
    S.promo = st.text_input("Promo code (optional)", S.promo).strip().upper()
    if S.promo and S.promo not in PROMOS:
        st.warning("Invalid promo code.")
    rows, sub, disc, ship, total = totals()
    st.markdown(f"**Subtotal:** ₹{sub:.0f}  \n**Discount:** −₹{disc:.0f}  \n**Shipping:** {'FREE' if not ship else '₹%d' % ship}  \n### Total: ₹{total:.0f}")
    st.caption("Go to **Checkout** in the sidebar to place your order.")

def page_about():
    st.title("🌿 About Petals Pavitra")
    show("logo.jpg", width=380)
    st.markdown(STORY, unsafe_allow_html=True)
    st.subheader("Our Mission")
    st.write("To give sacred temple flowers a second life as eco-friendly dhoop and spiritual products — "
             "reducing flower waste, supporting sustainable living and spreading positivity.")
    c1, c2 = st.columns(2)
    with c1: show("dhoop_card.jpg")
    with c2:
        st.subheader("Inside every box")
        st.write("🌺 Handcrafted dhoop  \n🌸 Natural fragrance  \n💚 Eco-friendly  \n🌍 Supports sustainable living")
        show("petals.jpg")
    st.subheader("Product label")
    show("label.jpg")
    st.subheader("👥 Our Team")
    st.caption("A sustainable step towards a greener tomorrow — presented by **Maya**, Team Leader")
    for col, (role, work) in zip(st.columns(len(TEAM)), TEAM):
        col.markdown(f"<div class='card' style='min-height:120px'><b>{role}</b><br><small>{work}</small></div>",
                     unsafe_allow_html=True)

def page_contact():
    st.title("📞 Contact & FAQ")
    st.markdown(f"**📧 Email:** {CONTACT['email']}  \n**☎️ Customer care:** {CONTACT['phone']}  \n"
                f"**📍 Address:** {CONTACT['address']}")
    st.subheader("Frequently asked questions")
    faq = {"What is the dhoop made of?": "Sandalwood, camphor, clove, neem leaf, cinnamon, rose water, oudh and a natural binding agent — recycled temple flowers give the colour and fragrance.",
           "How do I use it?": "Light the tip, let it burn for a few seconds, then place it in a holder and enjoy the fragrance.",
           "Is it safe?": "Keep away from children, pets and flammable materials. Use in a well-ventilated area and never leave it unattended.",
           "How do I pay?": "Pay by UPI (scan the QR, enter your UTR) or card. UPI orders are confirmed once the owner verifies the payment.",
           "Can I choose the gift box colour?": "Yes — Blush Pink + Sage Green or Lavender + White. Pick it on the Shop page."}
    for q, a in faq.items():
        with st.expander(q): st.write(a)

def page_policies():
    st.title("📜 Policies")
    st.caption("Please review and edit these with your own terms before going live.")
    with st.expander("🚚 Shipping & Delivery", expanded=True):
        st.write("Orders are dispatched after payment is verified, usually within 2–4 working days. Delivery takes "
                 "about 3–7 working days across India. Shipping fee and free-shipping limit are shown in your cart.")
    with st.expander("↩️ Returns & Refunds"):
        st.write("Since dhoop is a consumable product, we accept returns only for damaged, defective or wrong items "
                 f"reported within 48 hours of delivery with photos at {CONTACT['email']}. Approved refunds are made to the original payment source within 5–7 working days.")
    with st.expander("🔒 Privacy"):
        st.write("We collect your name, email, phone and delivery address only to process and deliver your order. "
                 "We never sell your data. Passwords are stored encrypted.")
    with st.expander("📄 Terms of Use"):
        st.write("Product photos are for illustration; fragrance and colour of handmade dhoop may vary slightly. "
                 "Prices are in INR and inclusive of taxes. Use dhoop only as directed on the label.")
    with st.expander("📮 Grievance contact"):
        st.write(f"{CONTACT['email']} · {CONTACT['phone']} · {CONTACT['address']}")

def make_qr(data):
    """Real, scannable QR. Uses the qrcode library; falls back to a free online QR service."""
    try:
        import qrcode
        buf = io.BytesIO(); qrcode.make(data).save(buf, format="PNG"); return buf.getvalue()
    except Exception:
        return "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + quote(data)

def page_checkout():
    st.title("💳 Checkout")
    if S.last_order:
        o = table("SELECT * FROM orders WHERE id=?", (S.last_order,)).iloc[0]
        st.success(f"🎉 Order {o['id']} placed!")
        if o.pay_status == "Awaiting verification":
            st.info("Your UPI payment will be verified by the owner shortly. Track it in **My Orders**.")
        invoice(o)
        if st.button("Continue shopping"):
            S.last_order = None; st.rerun()
        return
    rows, sub, disc, ship, total = totals()
    if not rows:
        st.info("Your cart is empty — add something from the Shop."); return
    st.subheader(f"Order total: ₹{total:.0f}")
    if "pending_oid" not in S:
        S.pending_oid = "PP-" + uuid.uuid4().hex[:6].upper()
    oid = S.pending_oid
    DEMO = str(secret("DEMO_MODE", "")).lower() in ("1", "true", "yes")   # card is only a simulation -> hidden on the live site
    method = st.radio("Payment method", ["UPI", "Credit/Debit Card"] if DEMO else ["UPI"], horizontal=True)
    if method == "UPI":
        upi, payee = get_setting("upi_id"), get_setting("payee")
        link = f"upi://pay?pa={upi}&pn={quote(payee)}&am={total:.2f}&cu=INR&tn={oid}"
        c1, c2 = st.columns([1, 2])
        c1.image(make_qr(link), width=230)
        c1.caption("Scan with GPay / PhonePe / Paytm")
        c2.markdown(f"**Pay ₹{total:.2f}** to **{payee}**  \nUPI ID: `{upi}`  \nOrder ref: `{oid}`")
        c2.markdown("1️⃣ Scan the QR and pay  \n2️⃣ Copy the **12-digit UTR / transaction ID** from your UPI app  \n"
                    "3️⃣ Fill the form below and press **Place Order**")
        if upi == UPI_ID:
            c2.warning("Demo UPI ID is active. Owner: set your real UPI ID in Owner Portal → ⚙️ Settings.")
    with st.form("checkout"):
        name = st.text_input("Full name", S.user["name"])
        phone = st.text_input("Phone number (10 digits)")
        addr = st.text_area("Delivery address")
        if method == "UPI":
            utr = st.text_input("UPI transaction / UTR number (12 digits)")
        else:
            st.caption("Card payment is a simulation (no real money is charged).")
            num = st.text_input("Card number (16 digits)")
            e1, e2 = st.columns(2)
            exp, cvv = e1.text_input("Expiry (MM/YY)"), e2.text_input("CVV", type="password")
        go = st.form_submit_button("✅ Place Order")
    if go:
        errs = []
        if not name.strip(): errs.append("Enter your name.")
        if not (phone.strip().isdigit() and len(phone.strip()) == 10): errs.append("Phone must be 10 digits.")
        if not addr.strip(): errs.append("Enter delivery address.")
        if method == "UPI":
            if not (utr.strip().isdigit() and len(utr.strip()) == 12):
                errs.append("UTR must be 12 digits (shown in your UPI app after paying).")
            elif not table("SELECT 1 FROM orders WHERE utr=?", (utr.strip(),)).empty:
                errs.append("This UTR was already used for another order.")
            ref, pstat = utr.strip(), "Awaiting verification"
        else:
            d, ex = num.replace(" ", ""), exp.strip()
            if not (d.isdigit() and len(d) == 16): errs.append("Card number must be 16 digits.")
            if not (len(ex) == 5 and ex[2] == "/" and ex[:2].isdigit() and 1 <= int(ex[:2]) <= 12): errs.append("Expiry must be MM/YY.")
            if not (cvv.isdigit() and len(cvv) == 3): errs.append("CVV must be 3 digits.")
            ref, pstat = "CARD-SIM", "Paid (simulated)"
        for e in errs: st.error(e)
        if not errs:
            placed = False
            try:
                run("""INSERT INTO orders(id,email,name,phone,address,items,subtotal,discount,shipping,total,
                       method,status,created,ts,pay_status,utr)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (oid, S.user["email"], name.strip(), phone.strip(), addr.strip(), json.dumps(rows),
                     float(sub), float(disc), float(ship), float(total), method, "Pending",
                     datetime.now().strftime("%d %b %Y, %I:%M %p"), time.time(), pstat, ref))
                placed = True
            except Exception as e:
                st.error(f"Could not save order: {e}")
            if placed:
                items = "\n".join(f"- {r['name']} x {r['qty']}" for r in rows)
                notify(f"🌸 New order {oid} — ₹{total:.0f}",
                       f"Order {oid}\nCustomer: {name} ({phone})\nAddress: {addr}\n{items}\n"
                       f"Total: ₹{total:.0f}\nPayment: {method} — {pstat}, ref {ref}",
                       secret("NOTIFY_TO") or secret("SMTP_USER"))
                notify(f"Your Petals Pavitra order {oid}",
                       f"Thank you for your order, {name}!\n\n{items}\nTotal: ₹{total:.0f}\n"
                       f"We will confirm your payment and ship soon.\n\nSacred flowers. A second life. 🌸",
                       S.user["email"])
                S.cart, S.promo, S.last_order = {}, "", oid
                del S["pending_oid"]
                st.rerun()

def page_my_orders():
    st.title("📦 My Orders")
    df = table("SELECT * FROM orders WHERE email=? ORDER BY ts DESC", (S.user["email"],))
    if df.empty:
        st.info("No orders yet.")
    for _, o in df.iterrows():
        with st.expander(f"{o['id']} · ₹{o.total:.0f} · {o.status}"):
            invoice(o)

# ───────────────────────── Owner pages ─────────────────────────
def page_dashboard():
    st.title("📊 Owner Dashboard")
    if PG: st.success("✅ Permanent database connected — your orders and products are safe.")
    else:
        st.error("⚠️ Temporary database! Orders and products will be LOST when the app restarts. Add DATABASE_URL in secrets (see DEPLOY.md).")
        st.caption(f"Secrets this app can see: {secret_names() or 'NONE'} — the list must include DATABASE_URL.")
    found = sum(img_b64(n) is not None for n in ALL_IMAGES)
    if found < len(ALL_IMAGES): st.warning(f"Only {found}/{len(ALL_IMAGES)} brand photos found. Upload assets_data.py to GitHub (next to app.py).")
    if OWNER_PIN == "pavitra2026": st.warning("Default owner PIN is in use. Set OWNER_PIN in secrets before going live.")
    df = table("SELECT * FROM orders")
    boxes, by_prod = 0, {}
    for _, o in df.iterrows():
        for i in json.loads(o["items"]):
            boxes += i["qty"]; by_prod[i["name"]] = by_prod.get(i["name"], 0) + i["qty"] * i["price"]
    c = st.columns(4)
    c[0].metric("Orders", len(df))
    paid = df[df.pay_status.fillna("").eq("Paid")]
    c[1].metric("Revenue received", f"₹{paid.total.sum():.0f}")
    c[2].metric("Boxes sold", boxes)
    c[3].metric("PPT estimate (₹150/box)", f"₹{boxes * BOX_EST}")
    st.metric("Pending orders", int((df.status == "Pending").sum()) if not df.empty else 0)
    if by_prod:
        st.subheader("Revenue by product")
        st.bar_chart(pd.Series(by_prod))

    st.subheader("🌸 Your products")
    gal = table("SELECT * FROM products ORDER BY id")
    gc = st.columns(4)
    for i, p in gal.iterrows():
        with gc[i % 4]:
            show_product(p)
            st.caption(f"{p['name']} · ₹{p.price:.0f}" + ("" if p.avail else " · out of stock"))

def page_owner_orders():
    st.title("📋 All Orders")
    df = table("SELECT * FROM orders ORDER BY ts DESC")
    if df.empty:
        st.info("No orders yet."); return
    st.dataframe(df[["id", "created", "name", "phone", "total", "method", "pay_status", "utr", "status"]])
    st.download_button("⬇️ Download all orders (CSV)", df.drop(columns=["ts"]).to_csv(index=False), "orders.csv", "text/csv")
    oid = st.selectbox("Select order", df.id)
    o = df[df.id == oid].iloc[0]
    c1, c2 = st.columns(2)
    new = c1.selectbox("Delivery status", STATUSES, index=STATUSES.index(o.status))
    if c1.button("Update status"):
        run("UPDATE orders SET status=? WHERE id=?", (new, oid)); st.rerun()
    if o.pay_status == "Awaiting verification":
        c2.warning(f"UTR given by customer: {o.utr}\nCheck it in your UPI app / bank statement.")
        if c2.button("💰 Mark payment received"):
            run("UPDATE orders SET pay_status='Paid' WHERE id=?", (oid,)); st.rerun()
    ids = [int(i["id"]) for i in json.loads(o["items"])]
    allp = table("SELECT * FROM products")
    for c, pid in zip(st.columns(max(len(ids), 1)), ids):
        m = allp[allp.id == pid]
        if not m.empty:
            with c: show_product(m.iloc[0], 100)
    invoice(o)
    with st.expander("🗑️ Delete this order (e.g. a test order)"):
        if st.checkbox(f"Yes, permanently delete order {oid}") and st.button("Delete order"):
            run("DELETE FROM orders WHERE id=?", (oid,)); st.rerun()

def page_settings():
    st.title("⚙️ Store Settings")
    with st.form("set"):
        upi = st.text_input("Your real UPI ID (money comes here)", get_setting("upi_id"))
        payee = st.text_input("Name shown in UPI app", get_setting("payee"))
        fee = st.number_input("Shipping fee (₹)", 0, 2000, int(float(get_setting("ship_fee") or 0)))
        free = st.number_input("Free shipping on orders above (₹)  (0 = always free)", 0, 100000, int(float(get_setting("free_above") or 0)))
        if st.form_submit_button("Save"):
            if "@" not in upi: st.error("Enter a valid UPI ID.")
            else:
                for k, v in [("upi_id", upi.strip()), ("payee", payee.strip()), ("ship_fee", fee), ("free_above", free)]:
                    run(UPSERT, (k, str(v)))
                st.success("Saved. Applies to all new orders.")
    st.caption(f"Database: {'Postgres (permanent)' if PG else 'SQLite (temporary)'} · "
               f"E-mail alerts: {'ON' if secret('SMTP_USER') and secret('SMTP_PASS') else 'OFF (set SMTP_USER / SMTP_PASS)'}")

def page_products():
    st.title("🧺 Manage Products")
    prods = table("SELECT * FROM products ORDER BY id")
    gc = st.columns(4)
    for i, p in prods.iterrows():
        with gc[i % 4]:
            show_product(p)
            st.caption(f"{p['name']} · ₹{p.price:.0f}" + ("" if p.avail else " · out of stock"))
    with st.expander("➕ Add new product"):
        with st.form("add"):
            n, d = st.text_input("Name"), st.text_area("Description")
            pr, em = st.number_input("Price (₹)", 1.0, 100000.0, 150.0), st.text_input("Emoji", "🌸")
            up = st.file_uploader("Product photo (optional)", type=["jpg", "jpeg", "png"])
            if st.form_submit_button("Add") and n:
                run("INSERT INTO products(name,descr,price,emoji,img_data) VALUES(?,?,?,?,?)",
                    (n, d, float(pr), em, photo_b64(up))); st.rerun()
    for _, p in prods.iterrows():
        with st.expander(f"{p.emoji} {p['name']} — ₹{p.price:.0f}" + ("" if p.avail else "  · OUT OF STOCK")):
            show_product(p, 180)
            with st.form(f"e{p.id}"):
                n, d = st.text_input("Name", p["name"]), st.text_area("Description", p.descr)
                pr, em = st.number_input("Price (₹)", 1.0, 100000.0, float(p.price)), st.text_input("Emoji", p.emoji)
                av = st.checkbox("Available for sale", bool(p.avail))
                up = st.file_uploader("Replace photo", type=["jpg", "jpeg", "png"], key=f"u{p.id}")
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Save"):
                    run("UPDATE products SET name=?,descr=?,price=?,emoji=?,img_data=?,avail=? WHERE id=?",
                        (n, d, float(pr), em, photo_b64(up) or (p.img_data or ""), int(av), int(p.id))); st.rerun()
                if c2.form_submit_button("🗑️ Delete"):
                    run("DELETE FROM products WHERE id=?", (int(p.id),)); st.rerun()

# ───────────────────────── Router ─────────────────────────
if not S.role:
    login_page()
else:
    pages = ({"🏠 Home": page_home, "🛍️ Shop": page_shop, "🌿 About & Team": page_about,
              "🛒 Cart": page_cart, "💳 Checkout": page_checkout, "📦 My Orders": page_my_orders,
              "📞 Contact & FAQ": page_contact, "📜 Policies": page_policies}
             if S.role == "customer" else
             {"📊 Dashboard": page_dashboard, "📋 Orders": page_owner_orders, "🧺 Products": page_products,
              "⚙️ Settings": page_settings})
    with st.sidebar:
        show("logo.jpg")
        st.caption(f"Hi, {S.user['name']} ({S.role})")
        choice = st.radio("Go to", list(pages))
        if S.role == "customer":
            st.write(f"🛒 Items in cart: {sum(S.cart.values())}")
        if st.button("Logout"):
            for k in ["role", "user", "cart", "promo", "last_order"]: del S[k]
            st.rerun()
    pages[choice]()
    st.divider()
    st.caption(f"🌸 Petals Pavitra · Sacred flowers. A second life. · {CONTACT['email']} · {CONTACT['phone']}")
