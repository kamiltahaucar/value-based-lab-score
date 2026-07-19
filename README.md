# Value-Based Laboratory Score — web calculator

A Streamlit web app that turns the Value-Based Laboratory Score spreadsheet into
an online calculator. Anyone can open the site, select an implementation level
for each item, and see their score (out of 100) update live — broken down by
domain, section and subheading — then download the result as CSV or Excel.

## Files

| File | Purpose |
|---|---|
| `streamlit_app.py` | The app |
| `value_based_items.json` | All 60 items, their hierarchy and weights (extracted from the Excel model) |
| `requirements.txt` | Python dependencies |
| `.streamlit/config.toml` | Theme |

## The scoring model

- **60 items** grouped into **5 domains** (total = 100 points):
  - Traceability through total testing process — **20** (38 items)
  - Level of automation and digitalization — **20** (7 items)
  - Quality of laboratory information — **20** (6 items)
  - Clinical interaction — **30** (5 items)
  - Innovation and research — **10** (4 items)
- Each item is scored at one level: **0 / 0.25 / 0.5 / 0.75 / 1**.
- **Item score = level × item weight**; the total is the sum of all item scores.
  (All items at 1 → 100; all at 0.5 → 50.)

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open http://localhost:8501

## Deploy on Streamlit Community Cloud (streamlit.app) — free

1. Put these files in a **public GitHub repository** (keep the folder structure,
   including `value_based_items.json` and `.streamlit/config.toml`).
2. Go to **https://share.streamlit.io** and sign in with GitHub.
3. Click **Create app → Deploy a public app from GitHub**.
4. Select your repository and branch, and set **Main file path** to
   `streamlit_app.py` (if the files sit in a subfolder, include it, e.g.
   `app/streamlit_app.py`).
5. Click **Deploy**. After the build you get a public URL like
   `https://your-app-name.streamlit.app` that anyone can use.

To update the app later, just push changes to GitHub — the site redeploys
automatically.

## Notes

- Nothing is stored on a server; each visitor's answers live only in their own
  browser session.
- **Weights are automatic.** Each process has a fixed total (20/20/20/30/10 = 100)
  and every item in it gets an equal share, so the total always stays 100 no
  matter how many items a process has.

## Adding, editing or removing an item

Edit only `value_based_items.json` — no code change, no weight math.

To **add** an item, copy this block into the `"items"` list (put it next to the
other items of the same subheading so it appears in the right place):

```json
{
  "id": "i61",
  "process": "Traceability through total testing process",
  "section": "Pre-analytical phase",
  "subheading": "Test request and demand management",
  "item": "My new item name",
  "explanation": "Short description shown under the item."
}
```

- `id` must be **unique** (any short text, e.g. `i61`).
- `process`, `section`, `subheading` must be spelled **exactly** like existing
  ones to land in the right tab/group. A new spelling creates a new group.
- No `weight` needed — the app recomputes shares automatically.

To **remove** an item, delete its block. To **edit** wording, change the `item`
or `explanation` text. Commit the change to GitHub and the site redeploys.

> Adding a brand-new **process** (a whole new domain) also needs its total added
> to `meta.process_order` and `meta.process_max`, and the five totals must still
> sum to 100.

