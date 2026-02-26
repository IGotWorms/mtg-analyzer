import streamlit as st
import requests
import re

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="cEDH Deck Analyzer", page_icon="🧙‍♂️", layout="wide")

# ==========================================
# API & PARSING HELPER FUNCTIONS
# ==========================================
def parse_decklist(raw_text):
    """Parses a standard MTG decklist into a list of clean card names."""
    deck =[]
    lines = raw_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        # Skip empty lines or category headers (e.g., // Commander, // Lands)
        if not line or line.startswith('//') or line.lower() in ['commander', 'deck', 'mainboard', 'sideboard']:
            continue
            
        # 1. Remove quantities like "1 ", "1x ", "2 " at the start of the line
        card_name = re.sub(r'^\d+x?\s+', '', line)
        
        # 2. Remove set codes and collector numbers like " (LCI) 123" or "[C19]"
        card_name = re.sub(r'\s+[\(\[].*$', '', card_name)
        
        # 3. Remove Moxfield specific tags like *CMDR* or *F*
        card_name = card_name.replace('*CMDR*', '').replace('*F*', '').replace('*E*', '').strip()
        
        if card_name:
            # Lowercase for easier matching later
            deck.append(card_name.lower())
            
    return deck

def format_commander_name(name):
    """Formats the commander name for EDHRec's JSON endpoint."""
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    return name.replace(' ', '-')

def get_edhrec_recommendations(commander_name):
    """Fetches high-synergy staples from EDHRec."""
    formatted_name = format_commander_name(commander_name)
    url = f"https://json.edhrec.com/pages/commanders/{formatted_name}.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []

    data = response.json()
    top_cards =[]
    try:
        # Traverse EDHRec's layout to find Top and High Synergy cards
        for lst in data['container']['json_dict']['cardlists']:
            if lst['header'] in ['Top Cards', 'High Synergy Cards']:
                for card in lst['cardviews']:
                    top_cards.append(card['name'])
    except KeyError:
        pass
    return top_cards

def get_scryfall_data(card_name):
    """Fetches live pricing and Mana Value from Scryfall."""
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def get_youtube_videos(commander_name, api_key):
    """Searches YouTube for highly relevant cEDH guides."""
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
st.markdown("Paste your decklist to analyze it against EDHRec synergies, get Scryfall pricing for missing staples, and find cEDH YouTube guides.")

# Sidebar for inputs
with st.sidebar:
    st.header("Deck Details")
    commander_input = st.text_input("Commander Name (e.g., Kinnan, Bonder Prodigy):")
    yt_key = st.text_input("YouTube API Key (Optional):", type="password")
    
    st.markdown("---")
    st.markdown("**Paste your decklist here:**")
    st.markdown("*(Supports Moxfield, Archidekt, ManaBox, or plain text)*")
    raw_decklist = st.text_area("Decklist", height=300, label_visibility="collapsed")
    
    analyze_btn = st.button("Analyze Deck", type="primary", use_container_width=True)

# ==========================================
# MAIN APP LOGIC
# ==========================================
if analyze_btn:
    if not commander_input or not raw_decklist:
        st.error("⚠️ Please provide both a Commander name and paste a decklist.")
        st.stop()

    # 1. Parse the Decklist
    with st.spinner("Parsing decklist..."):
        my_deck_lower = parse_decklist(raw_decklist)
    
    st.header(f"Commander: {commander_input}")
    st.metric(label="Total Cards Detected", value=len(my_deck_lower))

    # 2. Fetch EDHRec
    with st.spinner(f"Fetching top synergies for {commander_input} from EDHRec..."):
        edhrec_cards = get_edhrec_recommendations(commander_input)
        
        if not edhrec_cards:
            st.warning("Could not find EDHRec data. Please check the spelling of your Commander.")
            st.stop()

        # Find missing staples by checking against our lowercased decklist
        missing_staples =[c for c in edhrec_cards if c.lower() not in my_deck_lower]

    # 3. Display Missing Staples & Scryfall Prices
    st.subheader("🔥 Suggested High-Power Additions")
    st.markdown("These are the top synergistic cards for your commander that are **missing** from your current list.")
    
    if missing_staples:
        total_cost = 0.0
        cols = st.columns(2) # Display in two neat columns
        
        with st.spinner("Fetching live prices from Scryfall..."):
            # Limit to the top 10 missing staples so we don't spam the Scryfall API
            for i, card in enumerate(missing_staples[:10]):
                card_data = get_scryfall_data(card)
                
                if card_data:
                    price = card_data.get('prices', {}).get('usd')
                    cmc = card_data.get('cmc', 'N/A')
                    
                    price_val = float(price) if price else 0.0
                    total_cost += price_val
                    price_str = f"${price}" if price else "Price Unavailable"
                    
                    # Alternate between the two columns
                    col = cols[i % 2]
                    with col:
                        st.markdown(f"**{card}** (CMC: {cmc}) — TCGPlayer: `{price_str}`")
                        
        st.success(f"**Estimated Upgrade Cost (Top 10): ${total_cost:.2f}**")
    else:
        st.info("Wow! Your deck already includes all the top EDHRec staples!")

    # 4. Fetch YouTube Videos
    st.markdown("---")
    st.subheader("📺 Recommended Watchlist")
    if yt_key:
        with st.spinner("Searching YouTube for cEDH guides..."):
            videos = get_youtube_videos(commander_input, yt_key)
            if videos:
                for vid in videos:
                    title = vid['snippet']['title']
                    vid_id = vid['id']['videoId']
                    st.markdown(f"🎥 **[{title}](https://www.youtube.com/watch?v={vid_id})**")
            else:
                st.warning("No videos found. Check your API key or search quota.")
    else:
        st.info("Enter a YouTube API key in the sidebar to automatically search for Deck Tech videos.")
