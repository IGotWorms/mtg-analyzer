import streamlit as st
import requests
import re

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="cEDH Deck Analyzer", page_icon="🧙‍♂️", layout="wide")

# ==========================================
# API HELPER FUNCTIONS
# ==========================================
def get_moxfield_deck(deck_id):
    url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return response.json()

def format_commander_name(name):
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    return name.replace(' ', '-')

def get_edhrec_recommendations(commander_name):
    formatted_name = format_commander_name(commander_name)
    url = f"https://json.edhrec.com/pages/commanders/{formatted_name}.json"
    response = requests.get(url)
    if response.status_code != 200:
        return[]

    data = response.json()
    top_cards = []
    try:
        for lst in data['container']['json_dict']['cardlists']:
            if lst['header'] in ['Top Cards', 'High Synergy Cards']:
                for card in lst['cardviews']:
                    top_cards.append(card['name'])
    except KeyError:
        pass
    return top_cards

def get_scryfall_data(card_name):
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def get_youtube_videos(commander_name, api_key):
    if not api_key:
        return[]
    query = f"{commander_name} mtg commander deck tech cEDH"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&maxResults=3&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('items', [])
    return[]

# ==========================================
# USER INTERFACE
# ==========================================
st.title("🧙‍♂️ High-Power MTG Deck Analyzer")
st.markdown("Analyze your Moxfield deck against EDHRec synergies, get Scryfall pricing for missing staples, and find cEDH YouTube guides.")

# Sidebar for inputs
with st.sidebar:
    st.header("Settings")
    deck_url = st.text_input("Paste Moxfield Deck URL:")
    yt_key = st.text_input("YouTube API Key (Optional):", type="password")
    analyze_btn = st.button("Analyze Deck", type="primary")

# ==========================================
# MAIN APP LOGIC
# ==========================================
if analyze_btn and deck_url:
    try:
        deck_id = deck_url.split("/")[-1]
    except:
        st.error("Invalid Moxfield URL")
        st.stop()

    with st.spinner("Fetching deck from Moxfield..."):
        deck_data = get_moxfield_deck(deck_id)
        
    if not deck_data:
        st.error("Could not find deck. Make sure it is public!")
        st.stop()

    commanders = list(deck_data.get("commanders", {}).keys())
    if not commanders:
        st.error("No commander found in this decklist!")
        st.stop()
        
    commander_name = commanders[0]
    mainboard = list(deck_data.get("mainboard", {}).keys())

    # Display Basic Stats
    st.header(f"Commander: {commander_name}")
    st.metric(label="Total Mainboard Cards", value=len(mainboard))

    # Fetch EDHRec
    with st.spinner("Cross-referencing high-synergy staples from EDHRec..."):
        edhrec_cards = get_edhrec_recommendations(commander_name)
        missing_staples =[c for c in edhrec_cards if c not in mainboard]

    st.subheader("🔥 Suggested High-Power Additions")
    st.markdown("These are top synergistic cards for your commander that are **missing** from your current list.")
    
    # Process top 10 missing staples
    if missing_staples:
        total_cost = 0.0
        
        # Create columns for a nice layout
        cols = st.columns(2)
        
        with st.spinner("Fetching live prices from Scryfall..."):
            for i, card in enumerate(missing_staples[:10]):
                card_data = get_scryfall_data(card)
                if card_data:
                    price = card_data.get('prices', {}).get('usd')
                    cmc = card_data.get('cmc', 'N/A')
                    image_uri = card_data.get('image_uris', {}).get('normal', '')
                    
                    price_val = float(price) if price else 0.0
                    total_cost += price_val
                    price_str = f"${price}" if price else "N/A"
                    
                    # Alternate columns
                    col = cols[i % 2]
                    with col:
                        st.markdown(f"**{card}** (CMC: {cmc}) - TCGPlayer: `{price_str}`")
                        
        st.success(f"**Estimated Upgrade Cost (Top 10): ${total_cost:.2f}**")
    else:
        st.info("Your deck already includes all the top EDHRec staples!")

    # YouTube Videos
    st.subheader("📺 Recommended Watchlist")
    if yt_key:
        with st.spinner("Searching YouTube for cEDH guides..."):
            videos = get_youtube_videos(commander_name, yt_key)
            if videos:
                for vid in videos:
                    title = vid['snippet']['title']
                    vid_id = vid['id']['videoId']
                    st.markdown(f"- [{title}](https://www.youtube.com/watch?v={vid_id})")
            else:
                st.warning("No videos found or invalid API key.")
    else:
        st.info("Enter a YouTube API key in the sidebar to search for Deck Tech videos.")
