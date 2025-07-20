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
import os, html2text, requests, subprocess, platform
from dotenv import load_dotenv
from pyzotero import zotero

# %%

# name of parent deck
PARENT_DECK = "CMU.65.001 - Literature Review"

# libraries I want to use
libraries = [

    "63.003 Literature Review for CMU.44.004",
    "63.005 Review for CMU.44.006",
    "63.006 Qual Aim 1 - SCS, DRGS",
    "63.007 Qual Aim 2 - GABA, GLU NT Sensing",
    "63.008 Qual Aim 3 - ML-Enhanced Biosensing",
    "63.009 Literature Review for CMU.44.001",
    "63.010 Literature Review for CMU.44.007"
]

# %%
# ## main code
# ─── Config ────────────────────────────────────────────────────────────────
load_dotenv()
ZOTERO = zotero.Zotero(
    os.getenv("ZOTERO_USER_ID"),
    "user",  # Force to "user" to avoid .env parsing issues
    os.getenv("ZOTERO_API_KEY")
)
VERBOSE        = True   # ← flip to False to silence output
OPENAI_URL     = "https://api.openai.com/v1/chat/completions"
OPENAI_KEY     = os.getenv("OPENAI_API_KEY")
# Auto-detect Anki URL for WSL
import platform
if platform.system() == "Linux":
    try:
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                # Running in WSL, use Windows host IP
                windows_host = subprocess.check_output(
                    "cat /etc/resolv.conf | grep nameserver | awk '{print $2}'", 
                    shell=True
                ).decode().strip()
                ANKI_URL = f"http://{windows_host}:8765"
                if VERBOSE:
                    print(f"WSL detected, using Windows host: {windows_host}")
            else:
                ANKI_URL = "http://127.0.0.1:8765"
    except:
        ANKI_URL = "http://127.0.0.1:8765"
else:
    ANKI_URL = "http://127.0.0.1:8765"  # Windows/Mac

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

OFFLINE_MODE = False  # Global flag for offline mode

def existing_decks():
    global OFFLINE_MODE
    try:
        r = requests.post(ANKI_URL, json={"action":"deckNames","version":6}, timeout=2)
        r.raise_for_status()
        return set(r.json().get("result", []))
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        print("\n⚠️  Cannot connect to Anki!")
        print("Did you open Anki?")
        response = input("\nWould you like to continue in offline mode? Cards will be saved to a file. (y/n): ")
        if response.lower() == 'y':
            OFFLINE_MODE = True
            print("\n✓ Continuing in offline mode. Cards will be saved to 'anki_cards_export.txt'")
            return set()  # Return empty set in offline mode
        else:
            print("\nPlease:")
            print("1. Open Anki")
            print("2. Make sure AnkiConnect addon is installed")
            print("3. Try running this script again\n")
            exit(1)
    except Exception as e:
        print(f"\n❌ ERROR connecting to Anki: {str(e)}")
        exit(1)

def ensure_deck(deck):
    if not OFFLINE_MODE:
        requests.post(ANKI_URL, json={
            "action":"createDeck","version":6,"params":{"deck":deck}
        })

def push_card(deck, front, back):
    if OFFLINE_MODE:
        # Save to file in offline mode
        with open("anki_cards_export.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Deck: {deck}\n")
            f.write(f"Front: {front}\n")
            f.write(f"Back: {back}\n")
    else:
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
def run_pipeline(collection_name, parent_deck):

    PARENT_DECK    = f"{parent_deck}::{collection_name}"
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
    run_pipeline(collection_name,PARENT_DECK)

# Show completion message if in offline mode
if OFFLINE_MODE:
    print("\n✅ Offline mode complete!")
    print("Cards have been saved to: anki_cards_export.txt")
    print("\nTo import into Anki:")
    print("1. Open the anki_cards_export.txt file")
    print("2. Copy the cards you want to import")
    print("3. In Anki, use File → Import or manually create the cards")
