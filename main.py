import streamlit as st
import os
from phi.agent import Agent
from phi.model.groq import Groq
from ddgs import DDGS
import time
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

# Initialize page config
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="🌎",
    initial_sidebar_state="collapsed"
)

# Enhanced Custom CSS for improved UI
st.markdown("""
    <style>
    :root {
        --primary-color: #8b5cf6;
        --accent-color: #ec4899;
        --background-light: #1e293b;
        --text-color: #f8fafc;
        --hover-shadow: 0 8px 24px rgba(236, 72, 153, 0.3);
    }

    .main {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    .stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background: linear-gradient(135deg, var(--primary-color), var(--accent-color)) !important;
        border: none !important;
        color: white !important;
        font-weight: bold;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: var(--hover-shadow);
        filter: brightness(1.1);
    }

    .sidebar .element-container {
        background-color: var(--background-light);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    .stExpander {
        background-color: #262730;
        border-radius: 10px;
        padding: 1rem;
        border: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    .planner-card {
        background-color: #262730;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid #3d3e47;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    .travel-summary {
        background-color: #1e1f26;
        padding: 1.5rem;
        border-radius: 10px;
        margin-top: 1.5rem;
        border-left: 5px solid var(--primary-color);
    }

    .travel-summary h4 {
        color: var(--primary-color);
        margin-bottom: 0.5rem;
    }

    .spinner-text {
        font-size: 1.2rem;
        font-weight: bold;
        color: var(--primary-color);
    }

    .dest-image {
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        object-fit: cover;
        width: 100%;
        height: 180px;
        margin-bottom: 10px;
    }

    .dest-image:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
    }

    .gallery-container {
        display: flex;
        gap: 10px;
        margin-bottom: 2rem;
        overflow-x: auto;
        padding: 10px 0;
    }

    </style>
""", unsafe_allow_html=True)

def fetch_destination_images(query, max_images=4):
    """Fetch image URLs for a given destination using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            # We add keywords like 'tourism' and 'scenic' to get better travel photos
            search_query = f"{query} tourism scenic points"
            results = ddgs.images(
                search_query,
                region="wt-wt",
                safesearch="moderate",
                max_results=max_images
            )
            return [result['image'] for result in results if 'image' in result]
    except Exception as e:
        st.error(f"Image fetch error: {str(e)}")
        return []

# Main UI Layout Configuration
st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 2rem; text-align: center;">
    <h1 style="margin-bottom: 10px; font-size: 2.5rem;">🌎 AI Travel Planner</h1>
    <img src="https://img.icons8.com/clouds/200/airplane-take-off.png" width="180" style="margin-top: 0;">
</div>
""", unsafe_allow_html=True)

# Load API key from environment (set in .env file)
groq_api_key = os.environ.get("GROQ_API_KEY", "")

st.markdown('<div class="planner-card">', unsafe_allow_html=True)
st.markdown("### 🛫 Describe Your Trip")

selected_model = "openai/gpt-oss-120b"

col1, col2 = st.columns(2)
with col1:
    source = st.text_input("🛫 From (Source)", placeholder="e.g., Mumbai")
with col2:
    destination = st.text_input("🌍 To (Destination)", placeholder="e.g., Goa")

col3, col4 = st.columns(2)
with col3:
    duration = st.number_input("📅 How many days?", min_value=1, max_value=30, value=5)
with col4:
    budget = st.select_slider(
        "💰 Budget Level",
        options=["Budget", "Moderate", "Luxury"],
        value="Moderate"
    )

travel_style = st.multiselect(
    "🎯 Travel Style",
    ["Culture", "Nature", "Adventure", "Relaxation", "Food", "Shopping"],
    ["Culture", "Nature"]
)

transport_pref = st.multiselect(
    "🚄 Preferred Transport Mode",
    ["Flight", "Train", "Bus/Car", "Any"],
    ["Any"]
)

st.markdown('</div>', unsafe_allow_html=True)

# Initialize session state variables
if 'travel_plan' not in st.session_state:
    st.session_state.travel_plan = None
if 'qa_expanded' not in st.session_state:
    st.session_state.qa_expanded = False
if 'destination_images' not in st.session_state:
    st.session_state.destination_images = []

try:
    # Set API keys in environment variables
    os.environ["GROQ_API_KEY"] = groq_api_key

    # Initialize travel agent with Groq model
    travel_agent = Agent(
        name="Travel Planner",
        model=Groq(id=selected_model),
        instructions=[
            "You are a travel planning assistant.",
            "Write in a 'short readable mode' – highly scannable, brief, and very easy to read.",
            "Use short sentences, short bullet points, and avoid any unnecessary filler text or lengthy paragraphs.",
            "For EVERY recommended hotel, attraction, or restaurant, you MUST provide a direct Google Search or TripAdvisor link formatted nicely in Markdown.",
            "Example: [Search for Hotel Name](https://www.google.com/search?q=Hotel+Name+City)",
            "CRITICAL: Do NOT output any XML tags, <function> tags, or raw tool calls. Just present the final travel plan in clean markdown."
        ],
        show_tool_calls=False,  # Set this to False to hide internal function calls from the UI
        markdown=True
    )


    # Generate button
    if st.button("✨ Generate My Perfect Travel Plan", type="primary"):
        if not groq_api_key:
            st.warning("⚠️ Please provide a Groq API key to generate the plan.")
        elif source and destination:
            try:
                live_container = st.container()
                
                with st.spinner(f"🔍 Fetching stunning photos of {destination}..."):
                    fetched_imgs = fetch_destination_images(destination)
                    st.session_state.destination_images = fetched_imgs
                    
                    # Show images immediately while the travel plan generates
                    if fetched_imgs:
                        with live_container:
                            st.markdown("### 📸 Destination Highlights")
                            cols = st.columns(len(fetched_imgs))
                            for i, img_url in enumerate(fetched_imgs):
                                with cols[i]:
                                    st.markdown(f'<img src="{img_url}" class="dest-image">', unsafe_allow_html=True)
                    
                with st.spinner("✨ Generating detailed travel plan... (this takes a few moments)"):
                    prompt = f"""Create a short, highly readable travel plan from {source} to {destination} for {duration} days on a {budget} budget.
    Travel Styles: {', '.join(travel_style)}
    Preferred Transport: {', '.join(transport_pref)}

    FORMATTING RULES:
    - Keep output strictly brief and easy to read.
    - Avoid long paragraphs; rely heavily on clean bullet lists.
    - Keep descriptions of places limited to 1 short sentence.

    Ensure the itinerary includes:

    1. 🚀 How to Reach
    - Provide detailed options to reach the destination.
    - Include specific options with estimated durations and approximate costs.

    2. 🌞 Best Time to Visit
    - Ideal months and a brief weather note.

    3. 🏨 Accommodation Recommendations
    - 2-3 stays matching the implied budget with quick location notes.

    4. 🗺️ Day-by-Day Itinerary
    - 2-3 brief activities per day with 1-sentence descriptions.
    - Include local travel recommendations and off-the-beaten-path hidden gems (not just famous places).
    - Local experiences aligned with the requested travel style.
    - IMPORTANT: For the main attraction or location you mention in each day, add an EXACT placeholder like this: [IMAGE: Name of Place]. Add only ONE placeholder per day.

    5. 🍽️ Culinary Experiences
    - 3-4 local dishes or restaurants, emphasizing authentic local food suggestions.

    6. 💡 Practical Travel Tips
    - Brief local commute, etiquette, and safety pointers.

    7. 💰 Estimated Total Trip Cost
    - Breakdown of expenses (PLEASE SHOW ALL COSTS IN BOTH INDIAN RUPEES (INR) AND US DOLLARS (USD))
    - Total estimated cost in both INR and USD
    - Money-saving tips

    Please provide relevant Google Search or TripAdvisor links without fail.

    Format the response in a clear, easy-to-read markdown format with headings and bullet points.
                    """
                    response = travel_agent.run(prompt)
                    raw_content = response.content if hasattr(response, 'content') else str(response)
                    clean_response = raw_content.replace('∣', '|').replace('\n\n\n', '\n\n')

                    # Parse and replace [IMAGE: location] placeholders with actual images
                    import re
                    matches = set(re.findall(r'\[IMAGE:\s*(.*?)\]', clean_response, flags=re.IGNORECASE))
                    for place in matches:
                        try:
                            # fetch 1 image for this specific place
                            imgs = fetch_destination_images(place + " " + destination, max_images=1)
                            if imgs:
                                img_md = f'<br><img src="{imgs[0]}" style="border-radius: 12px; max-height: 250px; object-fit: cover; margin: 10px 0; width: 100%; box-shadow: 0 4px 15px rgba(0,0,0,0.3);"><br>'
                                # Replace ignoring case
                                clean_response = re.sub(rf'\[IMAGE:\s*{re.escape(place)}\]', img_md, clean_response, flags=re.IGNORECASE)
                            else:
                                clean_response = re.sub(rf'\[IMAGE:\s*{re.escape(place)}\]', "", clean_response, flags=re.IGNORECASE)
                        except Exception:
                            clean_response = re.sub(rf'\[IMAGE:\s*{re.escape(place)}\]', "", clean_response, flags=re.IGNORECASE)

                    st.session_state.travel_plan = clean_response
                
                # Trigger a rerun to show the plan and images outside the button block
                st.rerun()
            except Exception as e:
                st.error(f"Error generating travel plan: {str(e)}")
                st.info("Please try again in a few moments.")
        else:
            st.warning("Please enter both a source and a destination to get a plan.")

    # Persistent Output Section
    if st.session_state.travel_plan:
        st.divider()
        
        # Display Hero Gallery
        if st.session_state.destination_images:
            st.markdown("### 📸 Destination Highlights")
            cols = st.columns(len(st.session_state.destination_images))
            for i, img_url in enumerate(st.session_state.destination_images):
                with cols[i]:
                    st.markdown(f'<img src="{img_url}" class="dest-image">', unsafe_allow_html=True)
        
        # Display Plan
        st.markdown(st.session_state.travel_plan, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Application Error: {str(e)}")
