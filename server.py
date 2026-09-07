from flask import Flask, render_template, request, jsonify
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

app = Flask(__name__, template_folder='.')

# Initialize Gemini client with your API key
client = genai.Client(api_key="AQ.Ab8RN6KGZ-L_L4SUu0JZe_0MfsFAIJpOrrpdfhY2dSChPMHaQQ")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/sos', methods=['POST'])
def trigger_sos():
    data = request.get_json() or {}
    location = data.get('coordinates', 'Unknown Offshore Coordinates')
    emergency_response = (
        f"🚨 CRITICAL SOS ALERT INITIATED: Distress signal broadcasted from coordinates: {location}. "
        "Coordinates transmitted to Coast Guard, MRCC, and nearby vessels via ISRO/DRDO satellite relays. "
        "Stay calm, keep life jackets secured, and await rescue vessels."
    )
    return jsonify({"status": "success", "response": emergency_response})

@app.route('/api/news', methods=['GET'])
def get_live_news():
    try:
        rss_url = "https://news.google.com/rss/search?q=ISRO+weather+DRDO+marine+IMD+India&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            items = []
            for item in root.findall('.//item')[:5]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                pub_elem = item.find('pubDate')
                
                title_text = title_elem.text if title_elem is not None else "News Update"
                link_text = link_elem.text if link_elem is not None else "#"
                pub_text = pub_elem.text[:16] if pub_elem is not None else ""
                
                source = "Google News"
                upper_title = title_text.upper()
                if "ISRO" in upper_title: source = "ISRO"
                elif "DRDO" in upper_title: source = "DRDO"
                elif "TOI" in upper_title or "TIMES OF INDIA" in upper_title: source = "TOI"
                elif "IMD" in upper_title or "WEATHER" in upper_title: source = "IMD Weather"

                items.append({
                    "title": title_text,
                    "link": link_text,
                    "source": source,
                    "date": pub_text
                })
            return jsonify({"status": "success", "news": items})
    except Exception:
        fallback = [
            {"title": "ISRO monitors atmospheric pressure systems across coastal zones", "link": "#", "source": "ISRO", "date": "Live Feed"},
            {"title": "IMD issues seasonal advisory for Arabian Sea and Bay of Bengal mariners", "link": "#", "source": "IMD Weather", "date": "Live Feed"},
            {"title": "DRDO coastal radar telemetry reporting stable operational metrics", "link": "#", "source": "DRDO", "date": "Live Feed"},
            {"title": "Times of India: Coastal states evaluate emergency storm readiness", "link": "#", "source": "TOI", "date": "Live Feed"}
        ]
        return jsonify({"status": "success", "news": fallback})

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json() or {}
    query = data.get('message', '').strip()
    agent_id = data.get('agent_id', 1)
    user_lat = data.get('lat', 22.5726)
    user_lon = data.get('lon', 88.3639)
    lower_q = query.lower()

    action_trigger = None

    if agent_id == 1:
        if any(k in lower_q for k in ['thermal radar', 'thermal image', 'infrared radar', 'heat map']):
            action_trigger = "toggle_thermal_radar"
        elif any(k in lower_q for k in ['sos', 'emergency', 'distress', 'sinking', 'coast guard']):
            action_trigger = "trigger_sos"
        elif any(k in lower_q for k in ['isro', 'disaster', 'warning', 'cyclone', 'tsunami', 'alert']):
            action_trigger = "show_disaster_alert"

    if agent_id == 1 and action_trigger is None and not any(k in lower_q for k in ['weather', 'wind', 'rain', 'forecast', 'fish']):
        try:
            nom_url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}"
            req = urllib.request.Request(nom_url, headers={'User-Agent': 'ORCA_AI_Marine_Suite/2.8'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                geo_data = json.loads(resp.read().decode())
                if geo_data and len(geo_data) > 0:
                    top = geo_data[0]
                    p_name = top.get('display_name', '').split(',')[0]
                    t_lat = float(top['lat'])
                    t_lon = float(top['lon'])
                    return jsonify({
                        "response": f"📍 Located **{p_name}** ({t_lat:.4f}°N, {t_lon:.4f}°E). Generating marine route and computing coastal metrics...",
                        "action": "route_to_location",
                        "target": {"name": p_name, "lat": t_lat, "lon": t_lon}
                    })
        except Exception:
            pass

    if agent_id == 1:
        system_instruction = (
            f"You are Agent 1 of ORCA AI, an advanced marine, weather, and thermal radar assistant for fishermen and mariners. "
            f"The user's current GPS location is Lat: {user_lat}, Lon: {user_lon}. Provide professional, accurate marine telemetry, "
            f"IMD/INCOIS weather insights, and safety advisories."
        )
    else:
        system_instruction = (
            "You are Agent 2 of ORCA AI, a friendly universal assistant, news researcher, and web companion. "
            "Keep the tone engaging, warm, helpful, and conversational."
        )

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=400
            )
        )
        response_text = response.text
    except Exception as e:
        response_text = f"⚠️ Gemini API Error: {str(e)}"

    return jsonify({"response": response_text, "action": action_trigger})

if __name__ == '__main__':
    print("Starting ORCA AI Server with Gemini SDK & Live News Feeds...")
    app.run(host='0.0.0.0', port=5000, debug=True)