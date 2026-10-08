# 🌸 Petals Pavitra — Go-Live Guide (≈ 30 minutes, all free)

## 1. Permanent database (Supabase)
1. Sign up at https://supabase.com → **New project**. Region: *Mumbai (ap-south-1)*.
   Choose a DB password with only letters and numbers (no `@ : / # ?`). Save it.
2. Wait ~2 minutes. Click **Connect** (top bar) → choose **Session pooler** → copy the URI.
   It looks like `postgresql://postgres.abcd:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`.
   Replace `[YOUR-PASSWORD]` with your password. (Use the *pooler* link — the direct link does not work on Streamlit Cloud.)
3. You do NOT need to create tables. The app creates them on first start.

## 2. Code on GitHub
1. Edit `CONTACT` at the top of `app.py` (your real phone / email / address) and the **Policies** text if needed.
2. New **private** repo on github.com → upload everything from the zip (`app.py`, `requirements.txt`, `assets/`, `.gitignore`, `.streamlit/secrets.toml.example`, `DEPLOY.md`).

## 3. Deploy on Streamlit Cloud
1. https://share.streamlit.io → sign in with GitHub → **Create app** → pick the repo, branch `main`, file `app.py`.
2. Before clicking Deploy open **Advanced settings → Secrets** and paste (with your values):
```
DATABASE_URL = "postgresql://postgres.xxxx:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
OWNER_PIN = "your-strong-pin"
UPI_ID = "yourname@oksbi"
```
3. Click **Deploy**. Open the site → Owner login → Dashboard must show a green “Permanent database connected”.

## 4. E-mail alerts (optional but recommended)
Google Account → Security → turn on 2-Step Verification → search “App passwords” → create one.
Add `SMTP_USER`, `SMTP_PASS`, `NOTIFY_TO` to Secrets (see `.streamlit/secrets.toml.example`).
You will get an e-mail for every order and the customer gets a confirmation.

## 5. Test BEFORE announcing
1. Owner → ⚙️ Settings: check UPI ID, payee name, shipping fee, free-shipping limit.
2. Owner → 🧺 Products: add a **₹1 test product**.
3. As a customer: buy it, scan the QR with your phone, pay ₹1 (+shipping), enter the UTR, place order.
4. Owner → 📋 Orders: confirm UTR in your UPI app → **Mark payment received** → Shipped → Delivered.
5. Reboot the app (Streamlit menu → Reboot). Your data must still be there. Then delete/hide the test product.

## 6. Daily routine
Owner Portal → Orders → check UTR in your UPI/bank app → **Mark payment received** → pack → **Shipped** (send tracking on the customer's phone) → **Delivered**. Download CSV anytime.

## Go-live checklist
- [ ] OWNER_PIN set in Secrets (not the default)
- [ ] Real UPI ID saved; ₹1 test payment received in your bank
- [ ] CONTACT + Policies edited; label MRP (₹149) vs site price (₹150) matched
- [ ] Test product removed; e-mail alert received
- [ ] Share the `.streamlit.app` link on WhatsApp / Instagram 🎉

## Good to know
- **UPI is verified by you** (UTR check). Fully automatic payments need a gateway (Razorpay/Cashfree) — can be added later.
- **Supabase free projects pause after ~7 days of no activity.** Orders keep it active; if it pauses, click “Restore” in the Supabase dashboard.
- **Streamlit free apps sleep** when nobody visits for a while; the first visitor clicks “wake up”.
- **Custom domain** (www.petalspavitra.com) is not supported on the free plan; you can forward a domain to the app link.
- Customers cannot reset a forgotten password yet; you can delete the user row in Supabase → Table Editor → users so they can re-sign-up.
