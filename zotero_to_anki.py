# %% [markdown]
# ---
# 
# # Main Script to Run
# 
# ---

# %% 
# ## Steps
# 
# 1. Open a Paper on Zotero
# 2. Copy the paper into a text file named "paper.txt". Save this file into a folder named after the author. (ex. Doe et al., 2015)
# 3. Create annotations, extract them into a text file, and save them as "notes.txt"
# 4. Drag & drop the folders into the "_inbox" folder, in the same parent folder where all the paper folders are stored. The folders in the _inbox folder will be the ones that the script finds and acts on.
# 5. Run the Script 
# 6. A set of Anki flashcards will be generated


# %% # ## imports
import os, html2text, requests
from dotenv import load_dotenv
from pyzotero import zotero

# %%
# libraries I want to use
libraries = [
    "63.001 Neural Engineering and Signal Processing",
    "63.002 Nano-Scale Bioelectronics",
    "63.003 Literature Review for CMU.44.004",
    "63.004 Releasing Parylene C from Wafer",
    "65.006 Qual Aim 1 - Fab GABA, GLU Sensor",
    "65.007 Qual Aim 2 - Chronic NT Sensing",
    "65.008 Qual Aim 3 - ML-Enhanced Biosensing",
    "73.001 Pt Black Deposition",
    "79.002 Biosensors",
    "79.003 Biocompatibility",
    "79.006 Bionanomaterials",
    "79.008 Neuromodulation",
    "79.009 Electrochemistry",
    "79.010 Nociception",
    "79.012 Neuroregeneration",
    "79.013 Spike Sorting",
    "79.015 Neuroscience",
    "79.016 Surgery",
    "79.020 GABA and GLU Sensing",
    "79.022 Transparent Electrodes",
    "79.024 Polyimide Devices",
    "79.025 Stimulation Electrodes",
    "79.026 Platinum Black Electrodes"
]

# %%
# ## main code
# ─── Config ────────────────────────────────────────────────────────────────
load_dotenv()
ZOTERO = zotero.Zotero(
    os.getenv("ZOTERO_USER_ID"),
    os.getenv("ZOTERO_LIBRARY_TYPE", "user"),
    os.getenv("ZOTERO_API_KEY")
)
ANKI_URL       = "http://127.0.0.1:8765"
OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
OPENAI_KEY     = os.getenv("OPENAI_API_KEY")
VERBOSE        = True   # ← flip to False to silence output

H2M = html2text.HTML2Text();  H2M.ignore_links = True

# ─── Helpers ───────────────────────────────────────────────────────────────
def vprint(*msg):
    if VERBOSE: print(*msg)

def all_collections(limit=100):
    out, start = [], 0
    while True:
        page = ZOTERO.collections(limit=limit, start=start)
        out.extend(page)
        if len(page) < limit: break
        start += limit
    return out

def fetch_items(coll_key, limit=100):
    out, start = [], 0
    while True:
        page = ZOTERO.collection_items(coll_key, limit=limit, start=start)
        out.extend(page)
        if len(page) < limit: break
        start += limit
    return out

def existing_decks():
    r = requests.post(ANKI_URL, json={"action":"deckNames","version":6}).json()
    return set(r.get("result", []))

def ensure_deck(deck):
    requests.post(ANKI_URL, json={
        "action":"createDeck","version":6,"params":{"deck":deck}
    })

def push_card(deck, front, back):
    requests.post(ANKI_URL, json={
        "action":"addNotes","version":6,
        "params":{"notes":[{
            "deckName":deck,"modelName":"Basic",
            "fields":{"Front":front,"Back":back},
            "tags":["paper","notecard"]
        }]}
    })

def generate_cards(text):
    hdr = {"Content-Type":"application/json","Authorization":f"Bearer {OPENAI_KEY}"}
    data = {
        "model":"gpt-4.1-nano", 
        "temperature":0.7,
        "messages":[
            {"role":"system","content":(


                "You are a research assistant helping create flashcards from academic paper annotations.\n\n"
                "Instructions:\n"
                "1. Review the annotations and generate 5-15 thoughtful question-answer pairs.\n"
                "2. If there are less than 10 annotations, make one question/answer pair for each annotation.\n" 
                "3. Make questions and answers clear but concise.\n"
                "4. Always include the paper reference in the question.\n"
                "5. Format each card as:\n"
                "   Q: Question text, paper reference\n"
                "   A: Answer text\n\n"
                "The annotations follow below. Please convert them into flashcards following this format."
                
                )
            },
            {"role":"user","content":text}
        ]
    }
    r = requests.post(OPENAI_URL, headers=hdr, json=data).json()
    return r["choices"][0]["message"]["content"]

def parse_cards(txt):
    q, a, out = "", "", []
    for ln in txt.splitlines():
        ln = ln.strip()
        if ln.startswith("Q:"):
            if q and a: out.append((q,a))
            q, a = ln[2:].strip(), ""
        elif ln.startswith("A:"):   
            a = ln[2:].strip()
    if q and a: out.append((q,a))
    return out

# ─── Main ───────────────────────────────────────────────────────────────────
def run_pipeline(collection_name):

    PARENT_DECK    = f"CMU.49.007 Automated Literature Review::{collection_name}"
    vprint(f"Looking for collection: {collection_name}")

    # error handling for finding collections
    try:
        coll_key = next(
            c["data"]["key"] for c in all_collections()
            if c["data"]["name"] == collection_name
        )
        vprint("Collection key:", coll_key)
    except StopIteration:
        print(f"Error: Cannot find collection: {collection_name}")
        return

    items = fetch_items(coll_key)
    vprint(f"Total items pulled: {len(items)}")

    # split items
    notes = [i for i in items if i["data"]["itemType"]=="note"]

    # index every pulled item by key so we can walk parent links fast
    items_by_key = {i["key"]: i for i in items}

    def top_level_key(k):
        """Follow parentItem links until we reach a top‑level item."""
        while True:
            itm = items_by_key.get(k)
            parent = itm and itm["data"].get("parentItem")
            if not parent:
                return k          # k is now a top‑level item
            k = parent            # climb one level

    annos = {}
    for n in notes:
        md = H2M.handle(n["data"]["note"]).strip()
        head = md.lower()[:80]
        if "annotations" not in head:
            continue

        top_key = top_level_key(n["data"]["parentItem"])
        annos.setdefault(top_key, []).append(md)
        vprint(f"    • note {n['key']} bucketed under TOP {top_key}")

    # troubleshooting: used to make sure the right notes are captured
    for pid, txts in annos.items():
        print(f"PARENT {pid}: {len(txts)} annotation‑notes")
        # If you want to see the first 60 chars of each note:
        for t in txts:
            print("   ↳", repr(t[:60]))

    print(f"[+] Papers with matching notes: {len(annos)}")

    papers_by_id = {
        i["key"]: i for i in items
        if i["data"]["itemType"] in {"journalArticle","conferencePaper","report"}
    }
    vprint(f"Papers: {len(papers_by_id)}   Notes: {len(notes)}")

    decks_exist = existing_decks()

    for pid, txts in annos.items():
        paper = papers_by_id.get(pid)
        if not paper:
            vprint("Orphan note, skipping:", pid)
            continue

        creator = paper["data"]["creators"][0]
        author  = creator.get("lastName", "Unknown")
        year    = paper["data"].get("date", "")[:4] or "n.d."
        deck    = f"{PARENT_DECK}::{author} et al., {year}"

        # ── Skip the entire paper if its deck already exists ─────────
        if deck in decks_exist:
            vprint(f"Deck already exists → skip: {deck}")
            continue
        else:
            ensure_deck(deck)
            decks_exist.add(deck)
            vprint("Created deck:", deck)

        # ── Only reaches here if the deck is new ─────────────────────
        notes_block = "\n\n".join(txts)
        vprint(f"Generating cards for {author} {year}  (notes={len(txts)})")
        cards = parse_cards(generate_cards(notes_block))
        vprint(f"  → {len(cards)} cards")

        for q, a in cards:
            push_card(deck, q, a)

for collection_name in libraries:
    run_pipeline(collection_name)
