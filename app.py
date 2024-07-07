from flask import Flask, render_template, request, jsonify
import mysql.connector
import requests
import plotly.graph_objects as go

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Majicmen64',
    'database': 'food_calories'
}

# API key for Barcode Lookup
barcode_lookup_api_key = 'tm7ouf1rbs667q05sp4dj36dobbu9y'

@app.route('/')
def index():
    food_items = get_all_foods()
    graphJSON = generate_graph()  # Fetch and generate graph data
    return render_template('index.html', food_items=food_items, graphJSON=graphJSON)

@app.route('/add_food', methods=['POST'])
def add_food():
    try:
        data = request.form
        food_name = data['food_name']
        calories = data['calories']
        
        if not food_name or not calories:
            return jsonify({"status": "error", "message": "Food name and calories are required."})

        add_food_to_db(food_name, calories)
        return jsonify({"status": "success", "message": "Food added to database."})
    
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing required parameter: {str(e)}"}), 400
    
    except mysql.connector.Error as e:
        return jsonify({"status": "error", "message": f"MySQL Error: {str(e)}"}), 500
    
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error."}), 500

@app.route('/create_day', methods=['POST'])
def create_day():
    try:
        data = request.form
        day_name = data['day_name']
        food_ids = data.getlist('food_select')
        
        if not day_name or not food_ids:
            return jsonify({"status": "error", "message": "Day name and food selections are required."})

        create_day_in_db(day_name, food_ids)
        return jsonify({"status": "success", "message": "Day created successfully."})
    
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing required parameter: {str(e)}"}), 400
    
    except mysql.connector.Error as e:
        return jsonify({"status": "error", "message": f"MySQL Error: {str(e)}"}), 500
    
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error."}), 500

@app.route('/scan_barcode', methods=['POST'])
def scan_barcode():
    try:
        data = request.json
        barcode_value = data['barcode']
        
        if not barcode_value:
            return jsonify({"status": "error", "message": "Barcode not recognized."})
        
        food_name, calories = retrieve_food_info_from_api(barcode_value)
        
        if food_name and calories:
            return jsonify({"status": "success", "message": "Food information found.", "food_name": food_name, "calories": calories})
        else:
            return jsonify({"status": "error", "message": "Food information not found for barcode."})
    
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing required parameter: {str(e)}"}), 400
    
    except mysql.connector.Error as e:
        return jsonify({"status": "error", "message": f"MySQL Error: {str(e)}"}), 500
    
    except requests.RequestException as e:
        return jsonify({"status": "error", "message": f"Request Error: {str(e)}"}), 500
    
    except Exception as e:
        return jsonify({"status": "error", "message": "Internal server error."}), 500

def generate_graph():
    try:
        days, calories = get_daily_calories()
        fig = go.Figure(data=[go.Scatter(x=days, y=calories, mode='lines+markers')])
        fig.update_layout(title="Calorie Intake Over Days", xaxis_title="Days", yaxis_title="Calories")
        graphJSON = fig.to_json()
        return graphJSON
    
    except mysql.connector.Error as e:
        print(f"MySQL Error in generate_graph: {str(e)}")
        return None
    
    except Exception as e:
        print(f"Error in generate_graph: {str(e)}")
        return None

def add_food_to_db(food_name, calories):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO food (name, calories) VALUES (%s, %s)", (food_name, calories))
        conn.commit()
        print(f"Inserted {food_name} with {calories} calories into database.")
    
    except mysql.connector.Error as e:
        print(f"MySQL Error in add_food_to_db: {str(e)}")
        raise
    
    except Exception as e:
        print(f"Error in add_food_to_db: {str(e)}")
        raise
    
    finally:
        cursor.close()
        conn.close()

def create_day_in_db(day_name, food_ids):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO day (name) VALUES (%s)", (day_name,))
        day_id = cursor.lastrowid
        
        for food_id in food_ids:
            cursor.execute("INSERT INTO day_food (day_id, food_id) VALUES (%s, %s)", (day_id, food_id))
        
        conn.commit()
        print(f"Created day {day_name} with food IDs: {food_ids}")
    
    except mysql.connector.Error as e:
        print(f"MySQL Error in create_day_in_db: {str(e)}")
        raise
    
    except Exception as e:
        print(f"Error in create_day_in_db: {str(e)}")
        raise
    
    finally:
        cursor.close()
        conn.close()

def get_all_foods():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM food")
        foods = cursor.fetchall()
        return foods
    
    except mysql.connector.Error as e:
        print(f"MySQL Error in get_all_foods: {str(e)}")
        return []
    
    except Exception as e:
        print(f"Error in get_all_foods: {str(e)}")
        return []
    
    finally:
        cursor.close()
        conn.close()

def get_daily_calories():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT day.name, SUM(food.calories) FROM day
            JOIN day_food ON day.id = day_food.day_id
            JOIN food ON day_food.food_id = food.id
            GROUP BY day.name
        """)
        results = cursor.fetchall()
        days = [row[0] for row in results]
        calories = [float(row[1]) for row in results]
        return days, calories
    
    except mysql.connector.Error as e:
        print(f"MySQL Error in get_daily_calories: {str(e)}")
        return [], []
    
    except Exception as e:
        print(f"Error in get_daily_calories: {str(e)}")
        return [], []

    finally:
        cursor.close()
        conn.close()

def retrieve_food_info_from_api(barcode_value):
    try:
        food_name = None
        calories = None
        barcode_url = f"https://api.barcodelookup.com/v3/products?barcode={barcode_value}&key={barcode_lookup_api_key}"
        response = requests.get(barcode_url)
        
        if response.status_code == 200:
            data = response.json()
            print(f"API Response for {barcode_value}: {data}")  # Log API response for debugging
            
            if 'products' in data and len(data['products']) > 0:
                product = data['products'][0]
                food_name = product.get('product_name', 'Unknown')
                nutrition_facts = product.get('nutrition_facts', '')

                if nutrition_facts:
                    # Parse nutrition_facts to find Energy value
                    nutrition_json = {}
                    values = nutrition_facts.split(', ')
                    
                    for value in values:
                        key_value_pair = value.split(' ')
                        
                        if len(key_value_pair) >= 2:
                            key = ' '.join(key_value_pair[:-1])
                            value = key_value_pair[-1]
                            
                            if key:
                                nutrition_json[key] = value
                    
                    # Extract calories from nutrition_json
                    if 'Energy' in nutrition_json:
                        calories = nutrition_json['Energy'].split(' ')[1]  # Extract the numerical value

        else:
            print(f"Barcode lookup API failed for {barcode_value}. Status code: {response.status_code}")
        
        return food_name, calories
    
    except requests.RequestException as e:
        print(f"Request Error in retrieve_food_info_from_api: {str(e)}")
        return None, None
    
    except Exception as e:
        print(f"Error in retrieve_food_info_from_api: {str(e)}")
        return None, None


if __name__ == '__main__':
    app.run(debug=True)
