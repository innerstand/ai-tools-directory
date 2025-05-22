import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, request, jsonify, render_template
import requests
import json
import logging
import threading
import time
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder="static", static_url_path="")

# --- Airtable Configuration ---
AIRTABLE_API_KEY = "patkWHk5PobuWrFQY.849523ab2a64a7a9aa7e144d4567500d490d26b7b7624335a8f2fbd0d013b552"
AIRTABLE_BASE_ID = "appSAywDHqFKHKKf4"
AIRTABLE_EMAIL_TABLE = "Email List"
AIRTABLE_TOOLS_TABLE = "AI Tools"
AIRTABLE_EMAIL_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_EMAIL_TABLE}"
AIRTABLE_TOOLS_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TOOLS_TABLE}"

# --- Email Configuration (Simulated) ---
SENDER_EMAIL = "hey@innerstand.ai"

# --- Caching Configuration ---
CACHE_DURATION = 300  # 5 minutes in seconds
tools_cache = {
    "data": None,
    "timestamp": 0
}

def send_confirmation_email_async(recipient_email, name):
    """Simulate sending a confirmation email asynchronously"""
    # In a real implementation, this would connect to an SMTP server
    # For now, we just log that we would send an email
    app.logger.info(f"SIMULATED: Confirmation email to {recipient_email} from {SENDER_EMAIL}")
    return True

def submit_to_airtable_async(user_data):
    """Submit data to Airtable asynchronously"""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    airtable_data = {
        "records": [
            {
                "fields": {
                    "Name": user_data["name"],
                    "Email": user_data["email"],
                    "Company": user_data.get("company", "")
                }
            }
        ]
    }
    
    try:
        response = requests.post(
            AIRTABLE_EMAIL_API_URL, 
            headers=headers, 
            json=airtable_data,
            timeout=5  # Set a reasonable timeout
        )
        response.raise_for_status()
        app.logger.info(f"Successfully added {user_data['email']} to Airtable")
        
        # Send confirmation email in background
        send_confirmation_email_async(user_data["email"], user_data["name"])
        
    except Exception as e:
        app.logger.error(f"Error submitting to Airtable: {e}")

def get_tools_from_airtable():
    """Fetch tools data from Airtable with caching"""
    current_time = time.time()
    
    # Return cached data if it's still valid
    if tools_cache["data"] is not None and current_time - tools_cache["timestamp"] < CACHE_DURATION:
        app.logger.info("Returning cached tools data")
        return tools_cache["data"]
    
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        all_records = []
        params = {}
        
        # Airtable uses pagination, so we need to handle that
        while True:
            response = requests.get(
                AIRTABLE_TOOLS_API_URL,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            response_data = response.json()
            all_records.extend(response_data.get('records', []))
            
            # Check if there are more records to fetch
            offset = response_data.get('offset')
            if offset:
                params['offset'] = offset
            else:
                break
        
        # Transform Airtable records to our tools format
        tools = []
        for record in all_records:
            fields = record.get('fields', {})
            tool = {
                "name": fields.get('Name', ''),
                "description": fields.get('Description', ''),
                "department": fields.get('Department', ''),
                "category": fields.get('Category', ''),
                "skill_level": fields.get('Skill_Level', 'Intermediate / Low-code'),
                "pricing": fields.get('Pricing', ''),
                "website_url": fields.get('Website_URL', '')
            }
            tools.append(tool)
        
        # Update cache
        tools_cache["data"] = tools
        tools_cache["timestamp"] = current_time
        
        app.logger.info(f"Fetched {len(tools)} tools from Airtable and updated cache")
        return tools
        
    except Exception as e:
        app.logger.error(f"Error fetching tools from Airtable: {e}")
        
        # If we have cached data, return it even if it's expired
        if tools_cache["data"] is not None:
            app.logger.info("Returning expired cached tools data due to fetch error")
            return tools_cache["data"]
        
        # If no cached data, try to load from static JSON as fallback
        try:
            with open(os.path.join(app.static_folder, 'tools.json'), 'r') as f:
                tools = json.load(f)
                app.logger.info(f"Loaded {len(tools)} tools from static JSON as fallback")
                return tools
        except Exception as json_e:
            app.logger.error(f"Error loading tools from static JSON: {json_e}")
            return []  # Return empty list as last resort

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/tools.json")
def get_tools_json():
    """Return tools data from Airtable instead of static file"""
    tools = get_tools_from_airtable()
    return jsonify(tools)

@app.route("/api/submit-email", methods=["POST"])
def submit_email_api():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("name"):
        return jsonify({"success": False, "message": "Name and Email are required."}), 400

    user_data = {
        "name": data.get("name"),
        "email": data.get("email"),
        "company": data.get("company", "")
    }

    # Start a background thread to handle the Airtable submission
    # This prevents the API request from blocking the response
    threading.Thread(
        target=submit_to_airtable_async,
        args=(user_data,),
        daemon=True
    ).start()
    
    # Return success immediately without waiting for Airtable
    return jsonify({
        "success": True, 
        "message": "Your information has been submitted. You now have access to the directory."
    })

@app.route("/api/refresh-tools", methods=["GET"])
def refresh_tools_cache():
    """Force refresh the tools cache"""
    # Clear the cache timestamp to force a refresh
    tools_cache["timestamp"] = 0
    
    # Get fresh data
    tools = get_tools_from_airtable()
    
    return jsonify({
        "success": True,
        "message": f"Tools cache refreshed. {len(tools)} tools loaded.",
        "count": len(tools)
    })

if __name__ == "__main__":
    app.logger.info("Starting Flask app with Airtable integration for both email capture and tools data")
    app.run(host="0.0.0.0", port=os.getenv("PORT", 8080), debug=True)
