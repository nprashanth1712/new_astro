#importing dependices
from openai import OpenAI
import requests
import os
import time
from tools import tools
from flask import Flask, request, Response, session
from functions import *
import json
import secrets
import base64
from dotenv import load_dotenv

load_dotenv()

open_api_key = os.getenv('OPENAI_API_KEY')
if not open_api_key:
    raise ValueError('OPENAI_API_KEY environment variable not set')

client = OpenAI(api_key=open_api_key)
astro_api_key = os.getenv('astro_api_key', 'ab6d8cc84498f9daa5acf5ee9219f2ee')
user_id =os.getenv('user_id', '629203')


tools = tools

function_dispatch_table = {
    "get_current_date_time":get_current_date_time,
    "birth_details":birth_details,
    "astro_details":astro_details,
    "planets":planets,
    "ayanamsha":ayanamsha,
    "ghat_chakra":ghat_chakra,
    "general_house_report":general_house_report,
    "general_rashi_report":general_rashi_report,
    "general_ascendant_report":general_ascendant_report,
    "lalkitab_horoscope":lalkitab_horoscope,
    "lalkitab_debts":lalkitab_debts,
    "lalkitab_houses":lalkitab_houses,
    "lalkitab_planets":lalkitab_planets,
    "kalsarpa_details":kalsarpa_details,
    "manglik":manglik,
    "sadhesati_current_status":sadhesati_current_status,
    "sadhesati_life_details":sadhesati_life_details,
    "pitra_dosha_report":pitra_dosha_report,
    "horo_chart":horo_chart,
    "major_yogini_dasha":major_yogini_dasha,
    "sub_yogini_dasha":sub_yogini_dasha,
    "current_yogini_dasha":current_yogini_dasha,
    "major_vdasha":major_vdasha,
    "current_vdasha":current_vdasha,
    "current_vdasha_all":current_vdasha_all,
    "daily_nakshatra_prediction":daily_nakshatra_prediction,
    "basic_gem_suggestion":basic_gem_suggestion,
    "rudraksha_suggestion":rudraksha_suggestion,
    "kp_planets":kp_planets,
    "kp_house_cusps":kp_house_cusps,
    "kp_birth_chart":kp_birth_chart,
    "kp_house_significator":kp_house_significator,
    "kp_planet_significator":kp_planet_significator,
    "advanced_panchang":advanced_panchang,
    "hora_muhurta":hora_muhurta,
    "chaughadiya_muhurta":chaughadiya_muhurta,
    "basic_panchang":basic_panchang,
    "planet_ashtak":planet_ashtak,
    "sarvashtak":sarvashtak,
    "match_birth_details":match_birth_details,
    "match_ashtakoot_points":match_ashtakoot_points,
    "match_obstructions":match_obstructions,
    "match_astro_details":match_astro_details,
    "match_planet_details":match_planet_details,
    "match_manglik_report":match_manglik_report,
    "match_dashakoot_points":match_dashakoot_points,
    "papasamyam_details":papasamyam_details
     # Add other functions here as needed
}

assistant_id = "asst_4RbVdRRd6eJMRBjbrtQpscE7"  # Use your actual assistant ID
my_updated_assistant = client.beta.assistants.update(
   assistant_id,
   tools=tools
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16) 
# Setting a secret key for session management  store secret keys in environment variables or secure configuration files that are not included in the source code repository.

def create_new_thread():
    thread = client.beta.threads.create()
    return thread.id

def your_main_function(user_query, thread_id):
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_query
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )

        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            latest_message = messages.data[0]
            text = latest_message.content[0].text.value
            return text

        elif run_status.status == 'requires_action':
            required_actions = run_status.required_action.submit_tool_outputs.model_dump()
            tools_output = []

            for action in required_actions["tool_calls"]:
                func_name = action["function"]["name"]
                arguments = json.loads(action["function"]["arguments"])

                func = function_dispatch_table.get(func_name)
                if func:
                    result = func(**arguments)
                    output = json.dumps(result) if not isinstance(result, str) else result
                    tools_output.append({
                        "tool_call_id": action["id"],
                        "output": output
                    })
                else:
                    print(f"Function {func_name} not found")

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tools_output
            )

        else:
            time.sleep(1)

@app.route('/', methods=['POST'])
def handle_query():
    data = request.json
    user_query = data.get('query')
    if user_query:
        if 'thread_id' not in session:
            session['thread_id'] = create_new_thread()

        response = your_main_function(user_query, session['thread_id'])
        response_data = json.dumps({'response': response})
        return Response(response_data, mimetype='application/json')
    else:
        error_response_data = json.dumps({'error': 'No query provided'})
        return Response(error_response_data, mimetype='application/json', status=400)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
    from gunicorn.app.wsgiapp import WSGIApplication
    WSGIApplication("%(application)s").run()