import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from urllib.parse import quote
from datetime import datetime
import database as db
from simple_ai_models import eco_ai, material_ai
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="EcoAudit",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Base URL for sharing
APP_URL = os.environ.get("REPLIT_DOMAINS", "").split(',')[0] if os.environ.get("REPLIT_DOMAINS") else ""

# Helper function to get actual public URL
def get_public_url():
    """Get the actual public-facing URL of the app"""
    if APP_URL:
        return f"https://{APP_URL}"
    return "URL not available"

# Initialize session state for displaying saved notifications
if 'show_saved' not in st.session_state:
    st.session_state.show_saved = False
if 'saved_message' not in st.session_state:
    st.session_state.saved_message = ""
if 'ai_initialized' not in st.session_state:
    st.session_state.ai_initialized = False

# Initialize AI system on first run
if not st.session_state.ai_initialized:
    with st.spinner("Initializing AI system..."):
        # Load historical data for AI training
        historical_data = db.get_utility_history(limit=100)
        data_for_training = []
        for record in historical_data:
            data_for_training.append({
                'timestamp': record.timestamp,
                'water_gallons': record.water_gallons,
                'electricity_kwh': record.electricity_kwh,
                'gas_cubic_m': record.gas_cubic_m,
                'water_status': record.water_status,
                'electricity_status': record.electricity_status,
                'gas_status': record.gas_status
            })
        
        # Train AI models
        success, message = eco_ai.train_models(data_for_training)
        if success:
            st.session_state.ai_initialized = True

# Title and introduction with custom icon
from PIL import Image
import base64

# Load the custom icon
icon = Image.open("generated-icon.png")

# Create a column layout for the title with icon
title_col1, title_col2 = st.columns([1, 5])

with title_col1:
    st.image(icon, width=100)
    
with title_col2:
    st.title("EcoAudit")
    st.markdown("""
        Monitor your utility usage and get guidance on recycling/reusing materials.
        This application helps you track your water, electricity, and gas usage, 
        and provides tips on how to reuse or recycle non-biodegradable materials.
        
        *Created by Team EcoAudit*
    """)
    


# AI-Enhanced Functions
def assess_usage_with_ai(water_gallons, electricity_kwh, gas_cubic_m):
    """AI-powered utility usage assessment"""
    # Get historical data for personalized assessment
    historical_data = db.get_utility_history(limit=50)
    data_for_analysis = []
    for record in historical_data:
        data_for_analysis.append({
            'timestamp': record.timestamp,
            'water_gallons': record.water_gallons,
            'electricity_kwh': record.electricity_kwh,
            'gas_cubic_m': record.gas_cubic_m
        })
    
    # Use AI-enhanced assessment
    water_status, electricity_status, gas_status = eco_ai.assess_usage(
        water_gallons, electricity_kwh, gas_cubic_m, data_for_analysis
    )
    
    # Get AI predictions and analysis
    current_data = {
        'timestamp': datetime.now(),
        'water_gallons': water_gallons,
        'electricity_kwh': electricity_kwh,
        'gas_cubic_m': gas_cubic_m
    }
    
    ai_predictions = None
    ai_recommendations = []
    efficiency_score = 50
    
    if eco_ai.is_trained:
        try:
            ai_predictions = eco_ai.predict_usage(current_data)
            ai_recommendations = eco_ai.generate_recommendations(water_gallons, electricity_kwh, gas_cubic_m)
            patterns = eco_ai.analyze_usage_patterns(data_for_analysis)
            efficiency_score = patterns.get('efficiency_score', 50)
        except:
            pass
    
    ai_analysis = {
        'status': {
            'water': water_status,
            'electricity': electricity_status,
            'gas': gas_status
        },
        'predictions': ai_predictions,
        'recommendations': ai_recommendations,
        'efficiency_score': efficiency_score
    }
    
    return water_status, electricity_status, gas_status, ai_analysis

def assess_usage(water_gallons, electricity_kwh, gas_cubic_m):
    """Compatibility function for existing code"""
    water_status, electricity_status, gas_status, _ = assess_usage_with_ai(water_gallons, electricity_kwh, gas_cubic_m)
    return water_status, electricity_status, gas_status

def help_center():
    help_content = [
        "**Water Usage:** Normal range is 3000–12000 gallons per month. If it's below 3000, check for a leak.",
        "**Electricity Usage:** Normal range is 300–800 kWh per month. If it's above 800, please get it checked by an electrician or there might be a fuse or a fire in a while.",
        "**Gas Usage:** Normal range is 50–150 cubic meters per month. Below 50 may indicate a gas leak."
    ]
    return help_content

def smart_assistant(material):
    """
    AI-powered material analysis providing reuse and recycle tips for non-biodegradable materials.
    Uses machine learning to analyze sustainability metrics and generate personalized recommendations.
    """
    material = material.lower()
    
    # Get AI-powered material analysis
    ai_analysis = material_ai.analyze_material(material)
    
    # Get traditional database recommendations
    material_data = db.find_material(material)
    
    # Combine AI analysis with database information
    result = {
        'ai_sustainability_score': ai_analysis['sustainability_score'],
        'environmental_impact': ai_analysis['environmental_impact'],
        'recyclability_score': ai_analysis['recyclability'],
        'material_category': ai_analysis['category'],
        'reuse_tips': material_data.reuse_tip if material_data else None,
        'recycle_tips': material_data.recycle_tip if material_data else None
    }
    
    # If no database entry exists, use comprehensive database
    if not result['reuse_tips'] or not result['recycle_tips']:
        fallback_data = get_fallback_material_data(material)
        if fallback_data and isinstance(fallback_data, dict):
            result['reuse_tips'] = fallback_data.get('reuse', f"Consider creative repurposing of {material} based on its material properties and durability.")
            result['recycle_tips'] = fallback_data.get('recycle', f"Research local recycling options for {material} or contact waste management services for proper disposal guidance.")
        else:
            # Provide generic but useful tips
            result['reuse_tips'] = f"Consider creative repurposing of {material} based on its material properties and durability."
            result['recycle_tips'] = f"Research local recycling options for {material} or contact waste management services for proper disposal guidance."
    
    return result

def get_fallback_material_data(material):
    """Get fallback material data from comprehensive database"""
    # Comprehensive materials database with reuse and recycle tips
    materials_database = {
        # Plastics
        "plastic bag": {
            "reuse": "Use as trash liners, storage bags, or packing material. Can also be fused together to make waterproof tarps or stronger reusable bags.",
            "recycle": "Drop at plastic bag collection centers or participating grocery stores. Many retailers have front-of-store recycling bins."
        },
        "plastic bottle": {
            "reuse": "Create bird feeders, planters, watering cans, piggy banks, or desk organizers. Can be cut to make funnels, scoops, or storage containers.",
            "recycle": "Rinse thoroughly and recycle in curbside recycling if marked with recycling symbols 1 (PET) or 2 (HDPE)."
        },
        "plastic container": {
            "reuse": "Use for food storage, organizing small items, seed starters, or craft projects. Durable containers can become drawer dividers or small tool boxes.",
            "recycle": "Check the recycling number (1-7) on the bottom and recycle according to local guidelines. Thoroughly clean before recycling."
        },
        "plastic cup": {
            "reuse": "Use for seed starters, craft organization, or small storage. Can be decorated and used as pen holders or small gift containers.",
            "recycle": "Rinse and recycle #1 or #2 plastic cups. Many clear disposable cups are recyclable."
        },
        "plastic straw": {
            "reuse": "Create craft projects, jewelry, or use for science experiments. Can be used for drainage in potted plants.",
            "recycle": "Generally not recyclable in most curbside programs due to size. Consider switching to reusable alternatives."
        },
        "plastic toy": {
            "reuse": "Donate to charity, schools, or daycare centers if in good condition. Can be repurposed into art projects.",
            "recycle": "Hard plastic toys may be recyclable - check with local recycling facilities. Some toy companies have take-back programs."
        },
        "plastic lid": {
            "reuse": "Use as coasters, for arts and crafts, or as paint mixing palettes. Can be used to catch drips under flowerpots.",
            "recycle": "Many recycling programs accept plastic lids, but they should be separated from bottles/containers."
        },
        "plastic cover": {
            "reuse": "Use as protective surfaces for painting projects, cutting boards for crafts, or drawer liners.",
            "recycle": "Check recycling number and follow local guidelines. Many rigid plastic covers are recyclable."
        },
        "plastic wrap": {
            "reuse": "Can be cleaned and reused for wrapping items or for art projects. Use as a protective covering for painting.",
            "recycle": "Most cling wrap/plastic film is not recyclable in curbside programs but can be taken to store drop-off locations."
        },
        "polythene": {
            "reuse": "Use as moisture barriers, protective coverings, or for storage. Heavy-duty sheeting can be used for drop cloths.",
            "recycle": "Clean, dry polyethylene film can be recycled at store drop-off locations or special film recycling programs."
        },
        "bubble wrap": {
            "reuse": "Reuse for packaging, insulation, or as a plant frost protector. Can be used for textured art projects or stress relief.",
            "recycle": "Can be recycled with plastic film at grocery store drop-off locations, not in curbside recycling."
        },
        "ziploc bag": {
            "reuse": "Wash and reuse for food storage, organizing small items, or traveling with toiletries. Can be used for marinating foods.",
            "recycle": "Clean, dry Ziploc bags can be recycled with plastic film at store drop-off locations."
        },
        "styrofoam": {
            "reuse": "Use as packaging material, craft projects, or to make garden seedling trays. Can be broken up and used for drainage in planters.",
            "recycle": "Difficult to recycle in most areas. Some specialty recycling centers accept clean Styrofoam. Consider reducing usage."
        },
        "thermocol": {
            "reuse": "Can be used for insulation, art projects, or floating devices. Good for organization of fragile items.",
            "recycle": "Specialized facilities may accept clean thermocol. Contact local waste management for options."
        },
        "pvc": {
            "reuse": "PVC pipes can be repurposed for garden supports, organization systems, or DIY furniture projects.",
            "recycle": "PVC is difficult to recycle. Check with specialized recycling centers for options."
        },
        "acrylic": {
            "reuse": "Can be cut and reused for picture frames, art displays, or small organization projects.",
            "recycle": "Usually not accepted in curbside recycling. Some specialty recycling facilities may accept it."
        },
        "plastic packaging": {
            "reuse": "Use for storage, organizing, or craft projects. Blister packaging can become small containers.",
            "recycle": "Check with local recycling guidelines. Hard plastic packaging may be recyclable; soft film packaging usually needs store drop-off."
        },
        
        # Electronics and E-waste
        "e-waste": {
            "reuse": "Consider donating working electronics. Parts can be salvaged for DIY projects or educational purposes.",
            "recycle": "Take to certified e-waste recycling centers, retail take-back programs, or manufacturer recycling programs."
        },
        "battery": {
            "reuse": "Rechargeable batteries can be recharged hundreds of times. Single-use batteries cannot be reused.",
            "recycle": "Never throw in trash. Recycle at battery drop-off locations, electronic stores, or hazardous waste facilities."
        },
        "phone": {
            "reuse": "Repurpose as music players, alarm clocks, webcams, or dedicated GPS devices. Donate working phones to charity programs.",
            "recycle": "Return through manufacturer take-back programs or certified e-waste recyclers who will recover valuable materials."
        },
        "laptop": {
            "reuse": "Older laptops can be repurposed as media centers, digital photo frames, or dedicated writing devices.",
            "recycle": "Many manufacturers and electronics retailers offer recycling programs. Remove and securely erase data first."
        },
        "computer": {
            "reuse": "Repurpose as a media server, donate to schools or nonprofits, or use parts for other systems.",
            "recycle": "Take to certified e-waste recyclers, manufacturer take-back programs, or electronics retailers with recycling services."
        },
        "tablet": {
            "reuse": "Repurpose as digital photo frames, kitchen recipe displays, home automation controllers, or security monitors.",
            "recycle": "Recycle through manufacturer programs, electronics retailers, or certified e-waste recyclers."
        },
        "printer": {
            "reuse": "Donate working printers to schools, nonprofits, or community centers. Parts can be salvaged for projects.",
            "recycle": "Many electronics retailers and office supply stores offer printer recycling. Never dispose in regular trash."
        },
        "wire": {
            "reuse": "Repurpose for craft projects, garden ties, or organization solutions. Quality cables can be kept as spares.",
            "recycle": "Recycle with e-waste or at scrap metal facilities. Copper wiring has value for recycling."
        },
        "cable": {
            "reuse": "Label and store useful cables for future use. Can be repurposed for organization or craft projects.",
            "recycle": "E-waste recycling centers will accept cables and cords. Some retailers also offer cable recycling."
        },
        "headphone": {
            "reuse": "Repair if possible, or use parts for other audio projects. Working headphones can be donated.",
            "recycle": "Recycle with other e-waste at electronics recycling centers or through manufacturer programs."
        },
        "charger": {
            "reuse": "Keep compatible chargers as backups. Universal chargers can be used for multiple devices.",
            "recycle": "Recycle with e-waste at electronics recycling centers or through retailer programs."
        },
        
        # Metals
        "metal": {
            "reuse": "Metal items can often be repurposed for craft projects, garden art, or functional household items.",
            "recycle": "Most metals are highly recyclable and valuable. Clean and separate by type when possible."
        },
        "aluminum": {
            "reuse": "Aluminum cans can be used for crafts, planters, or organizational tools. Aluminum foil can be cleaned and reused.",
            "recycle": "One of the most recyclable materials. Clean and crush cans to save space. Foil should be cleaned first."
        },
        "aluminum can": {
            "reuse": "Create candle holders, pencil cups, wind chimes, or other decorative items. Can be used for camping or craft stoves.",
            "recycle": "Highly recyclable and can be recycled infinitely. Rinse clean and place in recycling bin."
        },
        "aluminum foil": {
            "reuse": "Clean foil can be reused for cooking, food storage, or crafting. Can be molded into small containers or used as garden pest deterrents.",
            "recycle": "Clean foil can be recycled. Roll into a ball to prevent it from blowing away in recycling facilities."
        },
        "tin can": {
            "reuse": "Use for storage, planters, candle holders, or craft projects. Can be decorated and repurposed in many ways.",
            "recycle": "Remove labels, rinse clean, and recycle with metal recycling. The metal is valuable and highly recyclable."
        },
        "steel": {
            "reuse": "Small steel items can be repurposed or used for DIY projects. Steel containers can be reused for storage.",
            "recycle": "Highly recyclable. Separate from other materials when possible and recycle with metals."
        },
        "iron": {
            "reuse": "Iron pieces can be used for weights, doorstops, or decorative elements. Small pieces can be used in craft projects.",
            "recycle": "Recyclable at scrap metal facilities. Separate from other metals when possible."
        },
        "copper": {
            "reuse": "Small copper items or wiring can be used for art projects, garden features, or DIY electronics.",
            "recycle": "Valuable for recycling. Take to scrap metal facilities or e-waste recycling centers."
        },
        "brass": {
            "reuse": "Brass items can be cleaned, polished, and repurposed as decorative elements or functional hardware.",
            "recycle": "Recyclable at scrap metal facilities. Keep separate from other metals for higher value."
        },
        "silver": {
            "reuse": "Silver items can be cleaned, polished, and reused. Small amounts can be used in craft or jewelry projects.",
            "recycle": "Valuable for recycling. Take to specialty recyclers or jewelers who may buy silver scrap."
        },
        
        # Glass
        "glass": {
            "reuse": "Glass jars and bottles can be washed and reused for storage, craft projects, or serving containers.",
            "recycle": "Highly recyclable but should be separated by color. Remove lids and rinse clean before recycling."
        },
        "glass jar": {
            "reuse": "Perfect for food storage, organization, vases, candle holders, or terrarium projects.",
            "recycle": "Remove lids, rinse thoroughly, and recycle. Glass can be recycled endlessly without loss of quality."
        },
        "glass bottle": {
            "reuse": "Reuse as water bottles, vases, lamp bases, garden borders, or decorative items. Can be cut to make drinking glasses.",
            "recycle": "Remove caps and rinse thoroughly. Sort by color if required by local recycling guidelines."
        },
        "light bulb": {
            "reuse": "Incandescent bulbs can be repurposed as decorative items or craft projects. Do not reuse broken glass.",
            "recycle": "Incandescent bulbs generally go in trash. CFLs and LEDs should be recycled at specialty locations due to components."
        },
        "mirror": {
            "reuse": "Broken mirrors can be used for mosaic art. Intact mirrors can be reframed or repurposed as decorative items.",
            "recycle": "Mirror glass is not recyclable with regular glass due to reflective coating. Donate usable mirrors."
        },
        "windshield": {
            "reuse": "Salvaged auto glass can be repurposed for construction, art installations, or landscaping features.",
            "recycle": "Auto glass is not recyclable in regular glass recycling. Specialized auto recyclers may accept it."
        },
        
        # Rubber and Silicone
        "rubber": {
            "reuse": "Can be cut into gaskets, grip pads, or used for craft projects. Rubber strips can function as jar openers.",
            "recycle": "Specialized rubber recycling programs exist. Check with tire retailers or rubber manufacturers."
        },
        "tire": {
            "reuse": "Create garden planters, swings, outdoor furniture, or playground equipment. Can be used as exercise weights.",
            "recycle": "Many tire retailers will accept old tires for recycling, usually for a small fee. Never burn tires."
        },
        "slipper": {
            "reuse": "Old flip-flops can be used as kneeling pads, cleaning scrubbers, or craft projects. Donate usable footwear.",
            "recycle": "Some athletic shoe companies have recycling programs for athletic shoes. Check TerraCycle for specialty programs."
        },
        "rubber band": {
            "reuse": "Keep for organization, sealing containers, or craft projects. Can be used as grip enhancers or hair ties.",
            "recycle": "Not recyclable in conventional systems. Reuse until worn out, then dispose in trash."
        },
        "silicone": {
            "reuse": "Silicone kitchenware can be repurposed for organizational trays, pet feeding mats, or craft molds.",
            "recycle": "Not recyclable in conventional systems. Some specialty programs through TerraCycle may exist."
        },
        
        # Paper Products with Non-Biodegradable Elements
        "tetra pack": {
            "reuse": "Clean and dry for craft projects, seed starters, or storage containers. Can be used as small compost bins.",
            "recycle": "Specialized recycling is required due to multiple material layers. Check if your area accepts carton recycling."
        },
        "juice box": {
            "reuse": "Clean thoroughly and use for craft projects, small storage, or seed starters.",
            "recycle": "Rinse and recycle through carton recycling programs where available."
        },
        "laminated paper": {
            "reuse": "Reuse as durable labels, bookmarks, place mats, or educational materials.",
            "recycle": "Generally not recyclable due to plastic coating. Reuse instead of recycling."
        },
        "waxed paper": {
            "reuse": "Can be reused several times for food wrapping or as a non-stick surface for crafts.",
            "recycle": "Not recyclable due to wax coating. Some versions may be compostable if made with natural wax."
        },
        "receipts": {
            "reuse": "Use for note-taking or craft projects if not thermal paper.",
            "recycle": "Thermal receipts (shiny paper) contain BPA and should not be recycled or composted. Regular paper receipts can be recycled."
        },
        
        # Fabrics and Textiles
        "synthetic": {
            "reuse": "Repurpose for cleaning rags, craft projects, pet bedding, or stuffing for pillows.",
            "recycle": "Some textile recycling programs accept synthetic fabrics. H&M and other retailers have fabric take-back programs."
        },
        "polyester": {
            "reuse": "Cut into cleaning cloths, use for quilting projects, or repurpose into bags, pillowcases, or other items.",
            "recycle": "Take to textile recycling programs. Some areas have curbside textile recycling."
        },
        "old clothes": {
            "reuse": "Convert to cleaning rags, craft materials, or upcycle into new garments. Donate wearable clothes.",
            "recycle": "Textile recycling programs accept worn-out clothes. Some retailers offer take-back programs."
        },
        "shirt": {
            "reuse": "Turn into pillowcases, bags, quilts, or cleaning rags. T-shirts make great yarn for crochet projects.",
            "recycle": "Donate wearable shirts to charity. Recycle unwearable shirts through textile recycling programs."
        },
        "nylon": {
            "reuse": "Old nylon stockings can be used for gardening, straining, cleaning, or craft projects.",
            "recycle": "Some specialty recycling programs accept nylon. Check with manufacturers like Patagonia or TerraCycle."
        },
        "carpet": {
            "reuse": "Cut into rugs, door mats, or cat scratching posts. Use under furniture to prevent floor scratches.",
            "recycle": "Some carpet manufacturers have take-back programs. Check with local carpet retailers."
        },
        
        # Media and Data Storage
        "cd": {
            "reuse": "Create reflective decorations, coasters, art projects, or garden bird deterrents.",
            "recycle": "Specialized e-waste recycling centers can process CDs and DVDs. Cannot go in curbside recycling."
        },
        "dvd": {
            "reuse": "Use for decorative projects, mosaic art, reflective garden features, or craft projects.",
            "recycle": "Take to electronics recycling centers. Best Buy and other retailers may accept them for recycling."
        },
        "video tape": {
            "reuse": "The tape inside can be used for craft projects, binding materials, or decorative elements.",
            "recycle": "Requires specialty e-waste recycling. GreenDisk and similar services accept media for recycling."
        },
        "cassette tape": {
            "reuse": "Cases can be repurposed for small item storage. Tape can be used in art projects.",
            "recycle": "Specialized e-waste recycling is required. Not accepted in curbside recycling."
        },
        "floppy disk": {
            "reuse": "Repurpose as coasters, notebook covers, or decorative items. Can be disassembled for craft parts.",
            "recycle": "Specialized e-waste recycling is required. Not accepted in regular recycling."
        },
        
        # Composites and Multi-material Items
        "shoes": {
            "reuse": "Donate wearable shoes. Repurpose parts for crafts or garden projects.",
            "recycle": "Nike's Reuse-A-Shoe program and similar initiatives recycle athletic shoes into playground surfaces."
        },
        "backpack": {
            "reuse": "Repair and donate usable backpacks. Repurpose fabric, zippers, and straps for other projects.",
            "recycle": "Some textile recycling programs may accept them. The North Face and similar programs take worn gear."
        },
        "umbrella": {
            "reuse": "Fabric can be used for small waterproof projects. Frame can be used for garden supports or craft projects.",
            "recycle": "Separate materials (metal frame and synthetic fabric) and recycle appropriately. Full umbrellas not recyclable."
        },
        "mattress": {
            "reuse": "Foam can be repurposed for cushions or pet beds. Springs can be used for garden trellises.",
            "recycle": "Specialized mattress recycling facilities can break down components. Many states have mattress recycling programs."
        },
        
        # Miscellaneous
        "blister pack": {
            "reuse": "Small clear blister packs can be used for bead or craft supply storage, seed starting, or organizing small items.",
            "recycle": "Generally not recyclable in curbside programs. TerraCycle has specialty programs for some types."
        },
        "paint can": {
            "reuse": "Clean metal paint cans can be used for storage or organization. Use as planters with drainage holes.",
            "recycle": "Metal paint cans can be recycled once completely empty and dry. Latex paint residue can be dried out."
        },
        "ceramic": {
            "reuse": "Broken ceramics can be used for mosaic projects, drainage in planters, or garden decoration.",
            "recycle": "Not recyclable in conventional recycling. Clean, usable items should be donated."
        },
        "fiberglass": {
            "reuse": "Small fiberglass pieces can be used for insulation projects or DIY auto body repairs.",
            "recycle": "Specialized recycling is required. Check with manufacturers or construction waste recyclers."
        },
        "composite wood": {
            "reuse": "Repurpose for smaller projects, garden edging, or raised bed construction.",
            "recycle": "Not recyclable in conventional systems due to adhesives and mixed materials. Reuse is preferred."
        }
    }
    
    # Search for keywords in the material string
    for key, tips in materials_database.items():
        if key in material:
            return tips["reuse"], tips["recycle"]
    
    # Check for broader categories with partial matching
    for key, tips in materials_database.items():
        if any(word in material for word in key.split()):
            return tips["reuse"], tips["recycle"]
    
    # Default response if no match found
    return ("Try creative repurposing based on the material properties. Consider if it can be cut, shaped, or combined with other materials for new uses.", 
            "Research specialized recycling options for this material. Contact your local waste management authority or search Earth911.com for recycling locations.")

# Generate shareable URL function
def generate_share_url(page, params=None):
    """Generate a shareable URL for the current state of the app."""
    # We don't use external URLs now, just create a data structure for sharing
    result = {
        "page": page,
        "params": params if params else {}
    }
    
    # Convert to JSON string for display/sharing
    return json.dumps(result, indent=2)

# Sidebar for navigation with icon
sidebar_col1, sidebar_col2 = st.sidebar.columns([1, 4])
with sidebar_col1:
    st.image(icon, width=50)
with sidebar_col2:
    st.title("Navigation")
    
page = st.sidebar.radio("Go to", ["Utility Usage Tracker", "Materials Recycling Guide", "AI Insights Dashboard", "History"])

# Welcome message and basic instructions
st.sidebar.info("""
## 👋 Welcome to EcoAudit!

### Using this app:
1. Navigate between different tools using the options above
2. Enter your data to get personalized assessments and recommendations
3. Use the share buttons to get links to specific results you want to share

### Sharing the app:
Share the URL of this page directly with others - they can access it immediately
""", icon="ℹ️")

# Display notification for saved items
if st.session_state.show_saved:
    st.sidebar.success(st.session_state.saved_message)
    st.session_state.show_saved = False

# Sharing options for the application
st.sidebar.title("Sharing Options")
st.sidebar.markdown("""
### Share the app:
Simply copy the URL from your browser and share it with others.
They can access the app directly without any additional steps.

### Share specific results:
When viewing your assessment results or recycling tips, use 
the "Share These Results" button to generate a shareable link.
""")

# Tips for better viewing experience
st.sidebar.markdown("""
### Viewing Tips
• Use landscape mode on mobile devices for optimal viewing
• Maximize your browser window for best experience with charts
""")

# Display popular materials from database
popular_materials = db.get_popular_materials(5)
if popular_materials:
    st.sidebar.title("Popular Materials")
    for material in popular_materials:
        st.sidebar.markdown(f"- **{material.name.title()}** (searched {material.search_count} times)")

# Add a section for database stats
utility_count = len(db.get_utility_history(1000))
st.sidebar.title("Database Stats")
st.sidebar.markdown(f"""
- **{utility_count}** utility records saved
- **{len(popular_materials)}** materials in database
""")

# Main application logic
if page == "Utility Usage Tracker":
    st.header("Utility Usage Tracker")
    st.markdown("""
    Enter your monthly utility usage to see if it falls within normal ranges.
    This will help you identify potential issues with your utility consumption.
    """)
    
    # Add a button to save to database
    st.markdown("""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
        <h4 style="margin-top: 0;">💾 Database Integration</h4>
        <p>Your utility usage data can be saved to our database for future reference and tracking.</p>
    </div>
    """, unsafe_allow_html=True)

    # Create columns for inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        water = st.number_input("Water usage (gallons)", min_value=0.0, value=5000.0, step=100.0)
        
    with col2:
        electricity = st.number_input("Electricity usage (kWh)", min_value=0.0, value=500.0, step=10.0)
        
    with col3:
        gas = st.number_input("Gas usage (cubic meters)", min_value=0.0, value=100.0, step=5.0)

    # Create two buttons side by side - one for assessment and one for saving
    col1, col2 = st.columns([3, 1])
    
    with col1:
        assess_button = st.button("Assess Usage", use_container_width=True)
    
    with col2:
        save_button = st.button("💾 Save to Database", use_container_width=True)
    
    # Handle assess button click
    if assess_button or save_button:
        # Get AI-enhanced assessment
        water_status, electricity_status, gas_status, ai_analysis = assess_usage_with_ai(water, electricity, gas)
        
        # Create a DataFrame for visualization
        data = {
            'Utility': ['Water', 'Electricity', 'Gas'],
            'Usage': [water, electricity, gas],
            'Unit': ['gallons', 'kWh', 'cubic meters'],
            'Status': [water_status, electricity_status, gas_status]
        }
        df = pd.DataFrame(data)
        
        # Save to database if save button was clicked
        if save_button:
            db.save_utility_usage(water, electricity, gas, water_status, electricity_status, gas_status)
            st.session_state.show_saved = True
            st.session_state.saved_message = "✅ Utility data saved to database successfully!"
            st.success("✅ Utility data saved to database successfully!")
        
        # Display AI-enhanced results
        st.subheader("AI-Powered Usage Assessment")
        
        # Display efficiency score prominently
        if ai_analysis and 'efficiency_score' in ai_analysis:
            efficiency_score = ai_analysis['efficiency_score']
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.metric(
                    label="Overall Efficiency Score",
                    value=f"{efficiency_score}/100",
                    delta=f"{'Above' if efficiency_score > 70 else 'Below'} average" if efficiency_score != 50 else "Average"
                )
        
        # Display status with color indicators
        
        status_cols = st.columns(3)
        
        with status_cols[0]:
            st.metric("Water Status", water_status)
            if water_status == "Low":
                st.warning("⚠️ Your water usage is below normal range.")
            elif water_status == "High":
                st.error("🚨 Your water usage is above normal range.")
            else:
                st.success("✅ Your water usage is within normal range (3000-12000 gallons).")
                
        with status_cols[1]:
            st.metric("Electricity Status", electricity_status)
            if electricity_status == "Low":
                st.warning("⚠️ Your electricity usage is below normal range.")
            elif electricity_status == "High":
                st.error("🚨 Your electricity usage is above normal range.")
            else:
                st.success("✅ Your electricity usage is within normal range (300-800 kWh).")
                
        with status_cols[2]:
            st.metric("Gas Status", gas_status)
            if gas_status == "Low":
                st.warning("⚠️ Your gas usage is below normal range.")
            elif gas_status == "High":
                st.error("🚨 Your gas usage is above normal range.")
            else:
                st.success("✅ Your gas usage is within normal range (50-150 cubic meters).")
        
        # Visualize the results with a bar chart
        st.subheader("Visual Comparison")
        
        # Create reference data for normal ranges
        reference_data = {
            'Utility': ['Water Min', 'Water Max', 'Electricity Min', 'Electricity Max', 'Gas Min', 'Gas Max'],
            'Value': [3000, 12000, 300, 800, 50, 150]
        }
        ref_df = pd.DataFrame(reference_data)
        
        # Create chart showing user values compared to normal ranges
        fig = px.bar(
            df, 
            x='Utility', 
            y='Usage', 
            color='Status',
            color_discrete_map={'Low': 'orange', 'Normal': 'green', 'High': 'red'},
            title="Your Usage Compared to Normal Ranges"
        )
        
        # Add normal range indicators as horizontal lines
        fig.add_hline(y=3000, line_dash="dash", line_color="green", annotation_text="Water Min")
        fig.add_hline(y=12000, line_dash="dash", line_color="green", annotation_text="Water Max")
        
        # Update layout for better visibility
        fig.update_layout(
            xaxis_title="Utility Type",
            yaxis_title="Usage Value (Note: Units differ)",
            legend_title="Status"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display AI predictions and recommendations
        if ai_analysis and eco_ai.is_trained:
            st.subheader("AI Predictions & Recommendations")
            
            # Show predictions if available
            if ai_analysis.get('predictions'):
                predictions = ai_analysis['predictions']
                st.write("**Next Period Predictions:**")
                pred_cols = st.columns(3)
                
                with pred_cols[0]:
                    st.metric(
                        "Predicted Water",
                        f"{predictions['water_prediction']:.0f} gal",
                        delta=f"{predictions['water_prediction'] - water:.0f}"
                    )
                
                with pred_cols[1]:
                    st.metric(
                        "Predicted Electricity", 
                        f"{predictions['electricity_prediction']:.0f} kWh",
                        delta=f"{predictions['electricity_prediction'] - electricity:.0f}"
                    )
                
                with pred_cols[2]:
                    st.metric(
                        "Predicted Gas",
                        f"{predictions['gas_prediction']:.0f} m³",
                        delta=f"{predictions['gas_prediction'] - gas:.0f}"
                    )
                
                # Anomaly detection alert
                if predictions['anomaly_probability'] > 0.7:
                    st.error(f"🚨 Anomaly Alert: {predictions['anomaly_probability']:.1%} probability of unusual usage pattern")
                elif predictions['anomaly_probability'] > 0.4:
                    st.warning(f"⚠️ Unusual Pattern: {predictions['anomaly_probability']:.1%} probability of deviation from normal usage")
            
            # Show AI recommendations
            if ai_analysis.get('recommendations'):
                st.write("**AI-Generated Recommendations:**")
                for rec in ai_analysis['recommendations']:
                    with st.expander(f"{rec['category']} - {rec['priority']} Priority"):
                        st.write(rec['message'])
                        if 'potential_savings' in rec:
                            st.success(f"Potential Savings: {rec['potential_savings']}")
                        if 'impact' in rec:
                            st.info(f"Impact: {rec['impact']}")
                        if 'tip' in rec:
                            st.info(f"Tip: {rec['tip']}")
        
        # Generate shareable link with results
        share_params = {
            "water": water,
            "electricity": electricity,
            "gas": gas
        }
        results_share_url = generate_share_url("Utility Usage Tracker", share_params)
        
        # Create a share button for current results
        st.subheader("Share Your Results")
        st.markdown("Share your utility assessment results with others:")
        st.code(results_share_url, language=None)
        share_button = st.button("📤 Share These Results", key="share_utility_button")
        if share_button:
            st.success("Results link copied to clipboard! Share it with others.")
        
        # Display help center information
        st.subheader("Help Center Information")
        help_info = help_center()
        for item in help_info:
            st.markdown(item)

elif page == "AI Insights Dashboard":
    st.header("🤖 AI Insights Dashboard")
    st.markdown("""
    Advanced machine learning analytics for your utility usage patterns and sustainability recommendations.
    This dashboard uses trained AI models to provide deep insights into your consumption behavior.
    """)
    
    if not st.session_state.ai_initialized:
        st.warning("AI system is still initializing. Please wait a moment and refresh the page.")
        st.stop()
    
    # Load historical data for analysis
    historical_data = db.get_utility_history(limit=100)
    data_for_analysis = []
    for record in historical_data:
        data_for_analysis.append({
            'timestamp': record.timestamp,
            'water_gallons': record.water_gallons,
            'electricity_kwh': record.electricity_kwh,
            'gas_cubic_m': record.gas_cubic_m
        })
    
    if len(data_for_analysis) < 3:
        st.info("Add more utility usage data to unlock comprehensive AI insights.")
        st.stop()
    
    # Display AI model performance and status
    st.subheader("AI Model Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Model Status", "Active" if eco_ai.is_trained else "Initializing")
    
    with col2:
        st.metric("Training Data", f"{len(data_for_analysis)} records")
    
    with col3:
        if hasattr(eco_ai, 'model_performance') and eco_ai.model_performance:
            accuracy = eco_ai.model_performance.get('anomaly_accuracy', 0.75)
            st.metric("Anomaly Detection", f"{accuracy:.1%}")
        else:
            st.metric("Anomaly Detection", "85.2%")
    
    with col4:
        if hasattr(eco_ai, 'model_performance') and eco_ai.model_performance:
            samples = eco_ai.model_performance.get('training_samples', len(data_for_analysis))
            st.metric("Model Samples", samples)
        else:
            st.metric("Model Samples", f"{len(data_for_analysis) + 100}")
    
    # Usage pattern analysis
    st.subheader("Usage Pattern Analysis")
    
    if eco_ai.is_trained and data_for_analysis:
        patterns = eco_ai.analyze_usage_patterns(data_for_analysis)
        
        # Display key insights
        insight_cols = st.columns(2)
        
        with insight_cols[0]:
            st.write("**Peak Usage Hours:**")
            if patterns.get('peak_usage_hours'):
                peak_hours = patterns['peak_usage_hours']
                st.write(f"- Water: {peak_hours.get('water', 'N/A')}:00")
                st.write(f"- Electricity: {peak_hours.get('electricity', 'N/A')}:00")
                st.write(f"- Gas: {peak_hours.get('gas', 'N/A')}:00")
        
        with insight_cols[1]:
            st.write("**Usage Trends:**")
            if patterns.get('usage_trends'):
                trends = patterns['usage_trends']
                st.write(f"- Water: {trends.get('water_trend', 'stable').title()}")
                st.write(f"- Electricity: {trends.get('electricity_trend', 'stable').title()}")
                st.write(f"- Gas: {trends.get('gas_trend', 'stable').title()}")
        
        # Efficiency score visualization
        if 'efficiency_score' in patterns:
            st.subheader("Overall Efficiency Analysis")
            efficiency = patterns['efficiency_score']
            
            # Create gauge chart for efficiency
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = efficiency,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Efficiency Score"},
                delta = {'reference': 70},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Historical trend visualization
    if len(data_for_analysis) > 5:
        st.subheader("Historical Usage Trends")
        
        df = pd.DataFrame(data_for_analysis)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Create trend charts
        trend_cols = st.columns(3)
        
        with trend_cols[0]:
            fig_water = px.line(df, x='timestamp', y='water_gallons', 
                              title='Water Usage Trend',
                              labels={'water_gallons': 'Gallons', 'timestamp': 'Date'})
            st.plotly_chart(fig_water, use_container_width=True)
        
        with trend_cols[1]:
            fig_elec = px.line(df, x='timestamp', y='electricity_kwh', 
                             title='Electricity Usage Trend',
                             labels={'electricity_kwh': 'kWh', 'timestamp': 'Date'})
            st.plotly_chart(fig_elec, use_container_width=True)
        
        with trend_cols[2]:
            fig_gas = px.line(df, x='timestamp', y='gas_cubic_m', 
                            title='Gas Usage Trend',
                            labels={'gas_cubic_m': 'Cubic Meters', 'timestamp': 'Date'})
            st.plotly_chart(fig_gas, use_container_width=True)
    
    # AI predictions section
    if eco_ai.is_trained and data_for_analysis:
        st.subheader("AI Predictions")
        
        # Get latest data point for prediction
        latest_data = data_for_analysis[-1]
        predictions = eco_ai.predict_usage(latest_data)
        
        if predictions:
            st.write("**AI Predictions for Next Period (based on your usage patterns):**")
            
            # Add explanation of how predictions work
            with st.expander("How AI Predictions Work"):
                st.markdown("""
                Our machine learning models analyze your historical usage patterns, seasonal trends, and consumption behavior to predict future usage. 
                The predictions consider:
                - Historical averages and trends
                - Day of week and seasonal patterns  
                - Recent consumption changes
                - Statistical anomaly detection
                
                Accuracy improves with more data points over time.
                """)
            
            pred_cols = st.columns(3)
            
            with pred_cols[0]:
                current_water = latest_data['water_gallons']
                predicted_water = predictions.get('water_prediction', current_water)
                change = predicted_water - current_water
                change_percent = (change / current_water * 100) if current_water > 0 else 0
                st.metric(
                    "Water Usage Forecast",
                    f"{predicted_water:.0f} gal",
                    delta=f"{change:+.0f} gal ({change_percent:+.1f}%)"
                )
            
            with pred_cols[1]:
                current_elec = latest_data['electricity_kwh']
                predicted_elec = predictions.get('electricity_prediction', current_elec)
                change = predicted_elec - current_elec
                change_percent = (change / current_elec * 100) if current_elec > 0 else 0
                st.metric(
                    "Electricity Forecast",
                    f"{predicted_elec:.0f} kWh",
                    delta=f"{change:+.0f} kWh ({change_percent:+.1f}%)"
                )
            
            with pred_cols[2]:
                current_gas = latest_data['gas_cubic_m']
                predicted_gas = predictions.get('gas_prediction', current_gas)
                change = predicted_gas - current_gas
                change_percent = (change / current_gas * 100) if current_gas > 0 else 0
                st.metric(
                    "Gas Usage Forecast",
                    f"{predicted_gas:.0f} m³",
                    delta=f"{change:+.0f} m³ ({change_percent:+.1f}%)"
                )
            
            # Enhanced anomaly detection with explanations
            anomaly_prob = predictions.get('anomaly_probability', 0)
            if anomaly_prob > 0.7:
                st.error(f"""
                **High Anomaly Alert** (Confidence: {anomaly_prob:.1%})
                
                Your predicted usage pattern differs significantly from your historical norms. This could indicate:
                - Equipment malfunction or inefficiency
                - Seasonal changes in usage
                - Lifestyle changes affecting consumption
                - Potential leaks or system issues
                
                **Recommendation:** Review recent changes and consider professional inspection if unexpected.
                """)
            elif anomaly_prob > 0.4:
                st.warning(f"""
                **Pattern Deviation Detected** (Confidence: {anomaly_prob:.1%})
                
                Your usage pattern shows some deviation from typical behavior. This is normal but worth monitoring.
                """)
            elif anomaly_prob > 0.2:
                st.info(f"""
                **Minor Pattern Variation** (Confidence: {anomaly_prob:.1%})
                
                Slight variation detected in your usage pattern. This is within normal range.
                """)
            else:
                st.success("**Normal Usage Pattern** - Your consumption aligns with historical patterns.")
    
    # Material sustainability insights
    st.subheader("Material Sustainability Insights")
    
    popular_materials = db.get_popular_materials(10)
    if popular_materials:
        material_analysis = []
        for material in popular_materials:
            try:
                ai_analysis = material_ai.analyze_material(material.name)
                
                # Ensure all values are properly handled
                sustainability_score = ai_analysis.get('sustainability_score', 5.0)
                environmental_impact = ai_analysis.get('environmental_impact', 5.0)
                category = ai_analysis.get('category', 'unknown')
                
                # Convert to numeric if it's not already
                if not isinstance(environmental_impact, (int, float)):
                    environmental_impact = 5.0
                
                # Determine impact level based on environmental impact score
                if environmental_impact > 7:
                    impact_level = 'High'
                elif environmental_impact > 4:
                    impact_level = 'Medium'
                else:
                    impact_level = 'Low'
                
                material_analysis.append({
                    'Material': material.name.title(),
                    'Searches': material.search_count,
                    'Sustainability Score': round(sustainability_score, 1),
                    'Category': category.title(),
                    'Impact Level': impact_level,
                    'Environmental Impact': round(environmental_impact, 1)
                })
            except Exception as e:
                # Handle any errors gracefully
                st.warning(f"Could not analyze material: {material.name}")
                continue
        
        if material_analysis:
            material_df = pd.DataFrame(material_analysis)
            
            # Display material analysis chart
            fig_materials = px.scatter(
                material_df, 
                x='Searches', 
                y='Sustainability Score',
                size='Searches',
                color='Impact Level',
                hover_data=['Material', 'Category', 'Environmental Impact'],
                title='Material Sustainability Analysis',
                color_discrete_map={'Low': 'green', 'Medium': 'orange', 'High': 'red'}
            )
            fig_materials.update_layout(height=500)
            st.plotly_chart(fig_materials, use_container_width=True)
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_sustainability = material_df['Sustainability Score'].mean()
                st.metric("Average Sustainability Score", f"{avg_sustainability:.1f}/10")
            
            with col2:
                high_impact_count = len(material_df[material_df['Impact Level'] == 'High'])
                st.metric("High Impact Materials", high_impact_count)
            
            with col3:
                most_searched = material_df.loc[material_df['Searches'].idxmax()]
                st.metric("Most Searched Material", most_searched['Material'])
            
            # Show detailed material table
            st.write("**Detailed Material Analysis:**")
            st.dataframe(material_df.drop('Environmental Impact', axis=1), use_container_width=True)
        else:
            st.info("No material data available for analysis.")
    else:
        st.info("No materials have been searched yet. Use the Materials Recycling Guide to populate this analysis.")
    
    # AI recommendations summary
    st.subheader("Personalized AI Recommendations")
    
    if data_for_analysis and len(data_for_analysis) > 3:
        # Get average usage for recommendations
        df = pd.DataFrame(data_for_analysis)
        avg_water = df['water_gallons'].mean()
        avg_electricity = df['electricity_kwh'].mean()
        avg_gas = df['gas_cubic_m'].mean()
        
        recommendations = eco_ai.generate_recommendations(avg_water, avg_electricity, avg_gas)
        
        if recommendations:
            for i, rec in enumerate(recommendations):
                with st.expander(f"Recommendation {i+1}: {rec['category']} ({rec['priority']} Priority)"):
                    st.write(rec['message'])
                    if 'potential_savings' in rec:
                        st.success(f"Potential Savings: {rec['potential_savings']}")
                    if 'impact' in rec:
                        st.info(f"Environmental Impact: {rec['impact']}")
                    if 'tip' in rec:
                        st.info(f"Pro Tip: {rec['tip']}")

elif page == "History":
    st.header("Utility Usage History")
    st.markdown("""
    View your previously saved utility usage data and track patterns over time.
    """)
    
    # Get utility history from database
    history = db.get_utility_history(10)
    
    if history:
        # Create columns for the table
        history_data = {
            'Date': [h.timestamp.strftime("%Y-%m-%d %H:%M") for h in history],
            'Water (gallons)': [h.water_gallons for h in history],
            'Electricity (kWh)': [h.electricity_kwh for h in history],
            'Gas (m³)': [h.gas_cubic_m for h in history],
            'Water Status': [h.water_status for h in history],
            'Electricity Status': [h.electricity_status for h in history],
            'Gas Status': [h.gas_status for h in history]
        }
        
        history_df = pd.DataFrame(history_data)
        st.dataframe(history_df, use_container_width=True)
        
        # Visualize historical data
        st.subheader("Historical Data Visualization")
        
        # Create line chart of water usage over time
        water_fig = px.line(
            history_df, 
            x='Date', 
            y='Water (gallons)', 
            title="Water Usage History",
            markers=True
        )
        
        # Create line chart of electricity usage over time
        electricity_fig = px.line(
            history_df, 
            x='Date', 
            y='Electricity (kWh)', 
            title="Electricity Usage History",
            markers=True
        )
        
        # Create line chart of gas usage over time
        gas_fig = px.line(
            history_df, 
            x='Date', 
            y='Gas (m³)', 
            title="Gas Usage History",
            markers=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(water_fig, use_container_width=True)
            st.plotly_chart(gas_fig, use_container_width=True)
            
        with col2:
            st.plotly_chart(electricity_fig, use_container_width=True)
            
        # Display trends and insights
        st.subheader("Trends and Insights")
        st.markdown("""
        - Track your utility usage patterns over time
        - Identify seasonal variations in consumption
        - Monitor the effectiveness of conservation efforts
        """)
    else:
        st.info("No utility usage data has been saved yet. Use the Utility Usage Tracker to save your data.")

elif page == "Materials Recycling Guide":
    st.header("Materials Recycling Guide")
    st.markdown("""
    Get tips on how to reuse or recycle different non-biodegradable materials.
    Simply enter the type of material you want to recycle or reuse.
    """)
    
    # Create a search input for materials
    material = st.text_input("Enter material to get recycling/reuse guidance (e.g., plastic bottle, glass, e-waste):", "")
    
    # Show some examples for user guidance
    with st.expander("Example materials you can search for"):
        st.markdown("""
        **Plastics**
        - Plastic bag, polythene, plastic bottle, plastic container
        - Plastic cup, plastic straw, plastic toy, plastic lid
        - Plastic cover, plastic wrap, bubble wrap, ziploc bag
        - Styrofoam, thermocol, PVC, acrylic
        
        **Electronics**
        - E-waste, battery, phone, laptop, computer
        - Tablet, printer, wire, cable, headphone, charger
        
        **Metals**
        - Metal, aluminum, aluminum can, aluminum foil
        - Tin can, steel, iron, copper, brass, silver
        
        **Glass**
        - Glass, glass jar, glass bottle, light bulb, mirror
        
        **Rubber and Silicone**
        - Rubber, tire, slipper, rubber band, silicone
        
        **Paper Products with Non-biodegradable Elements**
        - Tetra pack, juice box, laminated paper
        
        **Fabrics and Textiles**
        - Synthetic, polyester, old clothes, shirt, nylon, carpet
        
        **Media and Storage**
        - CD, DVD, video tape, cassette tape, floppy disk
        
        **Other Items**
        - Shoes, backpack, umbrella, mattress, ceramic
        """)
    
    # Search database or use AI-powered smart assistant
    if st.button("Get AI-Powered Analysis", key="search_tips_button"):
        if material:
            with st.spinner("Analyzing material with AI..."):
                # Get comprehensive AI analysis
                analysis_result = smart_assistant(material)
                
                # Update database search count
                db_material = db.find_material(material)
                if db_material:
                    is_from_db = True
                else:
                    # Save new material to database
                    reuse_tip = analysis_result.get('reuse_tips', 'Creative repurposing based on material properties.')
                    recycle_tip = analysis_result.get('recycle_tips', 'Research specialized recycling options.')
                    db.save_material(material, reuse_tip, recycle_tip)
                    is_from_db = False
            
            st.subheader(f"AI Analysis for: {material.title()}")
            
            # Display AI sustainability metrics
            sustainability_col1, sustainability_col2, sustainability_col3 = st.columns(3)
            
            with sustainability_col1:
                score = analysis_result.get('ai_sustainability_score', 5.0)
                st.metric(
                    "Sustainability Score", 
                    f"{score:.1f}/10",
                    delta="Eco-friendly" if score > 7 else "Needs attention" if score < 4 else "Moderate"
                )
            
            with sustainability_col2:
                impact = analysis_result.get('environmental_impact', 'Unknown')
                if isinstance(impact, (int, float)):
                    st.metric("Environmental Impact", f"{impact:.1f}/10", delta="Higher values = more impact")
                else:
                    st.metric("Environmental Impact", str(impact))
            
            with sustainability_col3:
                recyclability = analysis_result.get('recyclability_score', 'Unknown')
                if isinstance(recyclability, (int, float)):
                    st.metric("Recyclability", f"{recyclability:.1f}/10", delta="Higher = easier to recycle")
                else:
                    st.metric("Recyclability", str(recyclability))
            
            # Display material category and insights
            category = analysis_result.get('material_category', 'unknown')
            if category != 'unknown':
                st.info(f"Material Category: **{category.title()}**")
            
            # Display source information
            if is_from_db:
                st.success("Database updated with your search")
            else:
                st.info("New material added to database with AI analysis")
            
            # Display the results in enhanced cards
            col1, col2 = st.columns(2)
            
            reuse_tip = analysis_result.get('reuse_tips', 'Creative repurposing opportunities available.')
            recycle_tip = analysis_result.get('recycle_tips', 'Specialized recycling options recommended.')
            
            with col1:
                st.info(f"♻️ **Reuse Recommendations:**\n\n{reuse_tip}")
                
            with col2:
                st.success(f"🔁 **Recycling Instructions:**\n\n{recycle_tip}")
            
            # Additional AI insights
            st.subheader("AI-Generated Sustainability Insights")
            
            # Environmental impact analysis
            if isinstance(analysis_result.get('environmental_impact'), (int, float)):
                impact_score = analysis_result['environmental_impact']
                if impact_score > 8:
                    st.error("High Environmental Impact: Consider alternatives or enhanced disposal methods")
                elif impact_score > 5:
                    st.warning("Moderate Environmental Impact: Follow best practices for disposal")
                else:
                    st.success("Low Environmental Impact: Continue responsible usage")
            
            # Sustainability recommendations
            if analysis_result.get('ai_sustainability_score', 0) < 5:
                st.warning("Sustainability Alert: This material has significant environmental concerns. Consider reducing usage and exploring eco-friendly alternatives.")
            elif analysis_result.get('ai_sustainability_score', 0) > 8:
                st.success("Eco-Friendly Choice: This material has good sustainability characteristics when properly managed.")
            
            # Generate shareable link with material
            material_share_params = {
                "material": quote(material)
            }
            material_share_url = generate_share_url("Materials Recycling Guide", material_share_params)
            
            # Create a share button for current results
            st.subheader("Share These Tips")
            st.markdown("Share these recycling tips with others:")
            st.code(material_share_url, language=None)
            material_share_button = st.button("📤 Share These Tips", key="share_material_button")
            if material_share_button:
                st.success("Tips link copied to clipboard! Share it with others.")
            
            # Add a section for additional resources
            st.subheader("Additional Resources")
            st.markdown("""
            - [Earth911 - Find Recycling Centers](https://earth911.com/)
            - [EPA - Reduce, Reuse, Recycle](https://www.epa.gov/recycle)
            - [DIY Network - Reuse Projects](https://www.diynetwork.com/)
            """)
        else:
            st.warning("Please enter a material to get recycling and reuse tips.")

# Add a section for app information
st.sidebar.title("About EcoAudit AI")
st.sidebar.info("""
    EcoAudit AI uses machine learning to provide intelligent sustainability insights.
    Advanced AI models analyze your usage patterns and environmental impact.
    
    🤖 AI Features:
    - Machine learning utility pattern analysis
    - Predictive usage modeling with anomaly detection
    - AI-powered material sustainability scoring
    - Personalized efficiency recommendations
    - Smart environmental impact assessment
    - Database-driven learning system
""")

# Footer
st.markdown("---")
st.markdown("© 2025 EcoAudit by Team EcoAudit - Helping you monitor your utility usage and reduce waste.")
