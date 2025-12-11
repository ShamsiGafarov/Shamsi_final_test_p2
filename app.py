# file: app.py
# authors: Raphael, Shamsi, Michelle
# how to run Command Line Program: (py -> python.exe and <filename>)
# type the following in the commmand line: 'py app.py' 
# how to run Flask App: flask run 

import requests
import flask
import pyrebase  # Firebase SDK for Python
import time 
import datetime
from datetime import datetime
from flask import session
import os
from dotenv import load_dotenv

# create flask app
app = flask.Flask(__name__)
app.secret_key = 'recipe_finder_secret_key_2024'  # Needed for session


# Load environment variables from .env file
load_dotenv()


# Firebase configuration - WITH FALLBACK
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": "recipe-finder-199c1.firebaseapp.com",
    "projectId": "recipe-finder-199c1",
    "storageBucket": "recipe-finder-199c1.firebasestorage.app",
    "messagingSenderId": "776884550252",
    "appId": "1:776884550252:web:89ce787b03a5c586dbb649",
    "databaseURL": "https://recipe-finder-199c1-default-rtdb.firebaseio.com",
}

# ===== FIREBASE CONNECTION CHECK =====
print("🔥" * 50)
print("FIREBASE SETUP CHECK")
print("🔥" * 50)
print(f"Using API Key: {FIREBASE_CONFIG['apiKey'][:20]}...")
print(f"Project: {FIREBASE_CONFIG['projectId']}")
print("🔥" * 50)
# ===== END CHECK =====

# Initialize Firebase
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
auth = firebase.auth()
db = firebase.database()

# Admin and Moderator configuration
ADMIN_EMAIL = "thebestadmin@gmail.com"
MODERATOR_EMAILS = ["moderator1@gmail.com", "moderator2@gmail.com"]

# Spoonacular API
API_KEY = os.getenv("SPOONACULAR_API_KEY")
BASE_URL = "https://api.spoonacular.com/recipes/findByIngredients"

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLEMAPS_API_KEY")

# Update the get_recipes_by_ingredients function in app.py
def get_recipes_by_ingredients(ingredients, number=10):
    if not ingredients or not API_KEY:
        print("No ingredients provided or API key missing")
        return []
    
    # Clean and validate ingredients
    cleaned_ingredients = [ing.strip() for ing in ingredients if ing.strip()]
    if not cleaned_ingredients:
        return []
        
    # Prepare query parameters
    params = {
        "ingredients": ",".join(cleaned_ingredients),
        "number": number,
        "ranking": 1,  # 1 = maximize used ingredients
        "ignorePantry": True,
        "apiKey": API_KEY
    }

    try:
        print(f"Searching Spoonacular API with ingredients: {cleaned_ingredients}")
        response = requests.get(BASE_URL, params=params, timeout=15)

        if response.status_code != 200:
            print(f"Spoonacular API Error: {response.status_code} - {response.text}")
            return []

        recipes = response.json()
        print(f"Found {len(recipes)} recipes from Spoonacular")
        return recipes
        
    except requests.exceptions.RequestException as e:
        print(f"Spoonacular API request failed: {e}")
        return []
    except ValueError as e:
        print(f"JSON parsing failed: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

# Helper function to determine user role
def get_user_role(email):
    if email == ADMIN_EMAIL:
        return "admin"
    elif email in MODERATOR_EMAILS:
        return "moderator"
    else:
        return "recipe_seeker"  # Default role for new registrations
    

@app.route('/favorite_spoonacular_recipe', methods=['POST'])
def favorite_spoonacular_recipe():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to favorite recipes'})
    
    user = session['user']
    data = flask.request.json
    recipe_id = data.get('recipe_id')
    recipe_title = data.get('recipe_title')
    
    try:
        # Check if user already favorited this Spoonacular recipe
        existing_favorite = db.child("spoonacular_favorites").child(user['uid']).child(recipe_id).get()
        if existing_favorite.val():
            return flask.jsonify({'success': False, 'error': 'You have already favorited this recipe'})
        
        # Save favorite
        favorite_data = {
            'recipe_id': recipe_id,
            'recipe_title': recipe_title,
            'favorited_at': time.time(),
            'source': 'spoonacular'
        }
        db.child("spoonacular_favorites").child(user['uid']).child(recipe_id).set(favorite_data)
        
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})
    


@app.route('/bookmark_spoonacular_recipe', methods=['POST'])
def bookmark_spoonacular_recipe():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to bookmark recipes'})
    
    user = session['user']
    data = flask.request.json
    recipe_id = data.get('recipe_id')
    recipe_title = data.get('recipe_title')
    
    try:
        # Toggle bookmark
        existing_bookmark = db.child("spoonacular_bookmarks").child(user['uid']).child(recipe_id).get()
        
        if existing_bookmark.val():
            # Remove bookmark
            db.child("spoonacular_bookmarks").child(user['uid']).child(recipe_id).remove()
            return flask.jsonify({'success': True, 'bookmarked': False})
        else:
            # Add bookmark
            bookmark_data = {
                'recipe_id': recipe_id,
                'recipe_title': recipe_title,
                'bookmarked_at': time.time(),
                'source': 'spoonacular'
            }
            db.child("spoonacular_bookmarks").child(user['uid']).child(recipe_id).set(bookmark_data)
            return flask.jsonify({'success': True, 'bookmarked': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})

@app.route('/shopping_list_spoonacular/<recipe_id>')
def shopping_list_spoonacular(recipe_id):
    try:
        # Get recipe details from Spoonacular API
        url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        params = {
            "apiKey": API_KEY,
            "includeNutrition": False
        }
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return flask.render_template(
                'spoonacular_shopping_list.html', 
                error="Failed to load recipe information from Spoonacular API",
                google_maps_api_key=GOOGLE_MAPS_API_KEY
            )
        
        recipe_data = response.json()
        
        # Extract ingredients
        ingredients = []
        if 'extendedIngredients' in recipe_data:
            ingredients = [ingredient['original'] for ingredient in recipe_data['extendedIngredients']]
        
        recipe = {
            'id': recipe_id,
            'name': recipe_data.get('title', 'Unknown Recipe'),
            'ingredients': ingredients
        }
        
        return flask.render_template(
            'spoonacular_shopping_list.html', 
            recipe=recipe,
            google_maps_api_key=GOOGLE_MAPS_API_KEY
        )
    except Exception as e:
        print(f"Error loading Spoonacular shopping list: {e}")
        return flask.render_template(
            'spoonacular_shopping_list.html', 
            error="Failed to load shopping list",
            google_maps_api_key=GOOGLE_MAPS_API_KEY
        )

@app.route('/spoonacular_bookmarks.json')
def spoonacular_bookmarks_json():
    if not session.get('user'):
        return flask.jsonify([])
    
    user = session['user']
    
    try:
        spoonacular_bookmarks = db.child("spoonacular_bookmarks").child(user['uid']).get()
        bookmarked_recipes = []
        
        if spoonacular_bookmarks.each():
            for bookmark in spoonacular_bookmarks.each():
                bookmark_data = bookmark.val()
                recipe_data = {
                    'id': bookmark_data['recipe_id'],
                    'name': bookmark_data['recipe_title'],
                    'source': 'spoonacular',
                    'ingredients': ['Check original recipe for full ingredients']
                }
                bookmarked_recipes.append(recipe_data)
        
        return flask.jsonify(bookmarked_recipes)
    except Exception as e:
        print(f"Error fetching Spoonacular bookmarks: {e}")
        return flask.jsonify([])
    

@app.route('/saved_recipe/<recipe_id>')
def saved_recipe_detail(recipe_id):
    if not session.get('user'):
        flask.flash('Please log in to view recipe details', 'warning')
        return flask.redirect('/login')
    
    user = session['user']
    
    try:
        # Try to find the recipe in saved_recipes
        recipe = db.child("saved_recipes").child(user['uid']).child(recipe_id).get()
        
        if recipe.val():
            recipe_data = recipe.val()
            recipe_data['id'] = recipe_id
            return flask.render_template('saved_recipe_detail.html', recipe=recipe_data)
        else:
            flask.flash('Recipe not found', 'error')
            return flask.redirect('/saved_recipes')
            
    except Exception as e:
        print(f"Error fetching saved recipe: {e}")
        flask.flash('Error loading recipe details', 'error')
        return flask.redirect('/saved_recipes')

@app.route('/delete_saved_recipe', methods=['POST'])
def delete_saved_recipe():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to delete recipes'})
    
    user = session['user']
    data = flask.request.json
    recipe_id = data.get('recipe_id')
    recipe_source = data.get('recipe_source')
    
    try:
        if recipe_source == 'spoonacular':
            # Delete from saved_recipes
            db.child("saved_recipes").child(user['uid']).child(recipe_id).remove()
            # Also remove from favorites and bookmarks if they exist
            db.child("spoonacular_favorites").child(user['uid']).child(recipe_id).remove()
            db.child("spoonacular_bookmarks").child(user['uid']).child(recipe_id).remove()
        else:
            # Delete uploaded recipe
            db.child("recipes").child(recipe_id).remove()
            # Remove from favorites and bookmarks
            db.child("favorites").child(user['uid']).child(recipe_id).remove()
            db.child("bookmarks").child(user['uid']).child(recipe_id).remove()
        
        return flask.jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting recipe: {e}")
        return flask.jsonify({'success': False, 'error': str(e)})

@app.route('/save_spoonacular_recipe', methods=['POST'])
def save_spoonacular_recipe():
    print("=== SAVE RECIPE ENDPOINT CALLED ===")
    
    if not session.get('user'):
        print("User not logged in")
        return flask.jsonify({'success': False, 'error': 'Please log in to save recipes'})
    
    user = session['user']
    data = flask.request.json
    
    print(f"Received data from user {user['email']}: {data}")
    
    try:
        # Validate required fields
        if not data:
            return flask.jsonify({'success': False, 'error': 'No data received'})
        
        if not data.get('recipe_name'):
            return flask.jsonify({'success': False, 'error': 'Recipe name is required'})
        
        if not data.get('spoonacular_recipe_id'):
            return flask.jsonify({'success': False, 'error': 'Recipe ID is required'})
        
        # Process ingredients
        all_ingredients = data.get('all_ingredients', [])
        if isinstance(all_ingredients, str):
            all_ingredients = [ing.strip() for ing in all_ingredients.split(',') if ing.strip()]
        
        # Prepare recipe data
        recipe_data = {
            'name': data.get('recipe_name'),
            'ingredients': all_ingredients,
            'instructions': data.get('instructions', ''),
            'cooking_time': data.get('cooking_time'),
            'difficulty': data.get('difficulty', 'Medium'),
            'created_at': time.time(),
            'created_at_readable': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': user['uid'],
            'user_email': user['email'],
            'source': 'spoonacular',
            'spoonacular_id': data.get('spoonacular_recipe_id'),
            'original_url': f"https://spoonacular.com/recipes/{data.get('recipe_name', '').replace(' ', '-')}-{data.get('spoonacular_recipe_id')}",
            'saved_at': time.time(),
            'saved_at_readable': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Remove None values
        recipe_data = {k: v for k, v in recipe_data.items() if v is not None}
        
        print(f"Saving recipe to database: {recipe_data['name']}")
        
        # Save to database
        db.child("saved_recipes").child(user['uid']).push(recipe_data)
        
        print("Recipe saved successfully!")
        return flask.jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving Spoonacular recipe: {str(e)}")
        import traceback
        traceback.print_exc()
        return flask.jsonify({'success': False, 'error': f'Server error: {str(e)}'})
    

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST':
        try:
            email = flask.request.form.get('email', '').strip()
            password = flask.request.form.get('password', '').strip()
            
            if not email or not password:
                return flask.render_template(
                    'login.html', 
                    error="Please fill in all fields",
                    email=email
                )
            
            # Firebase authentication
            user = auth.sign_in_with_email_and_password(email, password)
            
            # Get user role
            user_role = get_user_role(email)
            
            # Store user info in session
            session['user'] = {
                'uid': user['localId'],
                'email': email,
                'idToken': user['idToken'],
                'role': user_role
            }
            
            flask.flash('Login successful!', 'success')
            return flask.redirect('/')
            
        except Exception as e:
            error_message = str(e)
            if "INVALID_LOGIN_CREDENTIALS" in error_message:
                error_message = "Invalid email or password"
            elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
                error_message = "Too many attempts. Please try again later."
            
            return flask.render_template(
                'login.html', 
                error=error_message,
                email=email
            )
    
    return flask.render_template('login.html')


# Update the registration route in app.py
@app.route('/register', methods=['GET', 'POST'])
def register():
    if flask.request.method == 'POST':
        try:
            email = flask.request.form.get('email', '').strip()
            password = flask.request.form.get('password', '').strip()
            confirm_password = flask.request.form.get('confirm_password', '').strip()
            role = flask.request.form.get('role', 'recipe_seeker')  # Get role from form
            
            # Validation
            if not email or not password or not confirm_password:
                return flask.render_template(
                    'register.html', 
                    error="Please fill in all fields",
                    email=email
                )
            
            if password != confirm_password:
                return flask.render_template(
                    'register.html', 
                    error="Passwords do not match",
                    email=email
                )
            
            if len(password) < 6:
                return flask.render_template(
                    'register.html', 
                    error="Password must be at least 6 characters long",
                    email=email
                )
            
            # Firebase registration
            user = auth.create_user_with_email_and_password(email, password)
            
            # Determine role - use form role unless email is admin/moderator
            if email == ADMIN_EMAIL:
                user_role = "admin"
            elif email in MODERATOR_EMAILS:
                user_role = "moderator"
            else:
                user_role = role  # Use the role from the form
            
            # Store user info in session
            session['user'] = {
                'uid': user['localId'],
                'email': email,
                'idToken': user['idToken'],
                'role': user_role
            }
            
            # Store user data in database with the correct role
            user_data = {
                'email': email,
                'role': user_role,
                'created_at': time.time(),
                'created_at_readable': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            db.child("users").child(user['localId']).set(user_data)
            
            flask.flash(f'Registration successful! Welcome to Recipe Finder as a {user_role.replace("_", " ").title()}!', 'success')
            return flask.redirect('/')
            
        except Exception as e:
            error_message = str(e)
            if "EMAIL_EXISTS" in error_message:
                error_message = "An account with this email already exists"
            elif "WEAK_PASSWORD" in error_message:
                error_message = "Password is too weak. Please choose a stronger password."
            
            return flask.render_template(
                'register.html', 
                error=error_message,
                email=email
            )
    
    return flask.render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flask.flash('You have been logged out successfully.', 'info')
    return flask.redirect('/')

# Profile route
@app.route('/profile')
def profile():
    if not session.get('user'):
        flask.flash('Please log in to view your profile', 'warning')
        return flask.redirect('/login')
    
    user = session['user']
    return flask.render_template('profile.html', user=user)


@app.context_processor
def inject_global_vars():
    user = session.get('user')
    return dict(
        user=user,
        google_maps_api_key=GOOGLE_MAPS_API_KEY
    )

# Webapp version
@app.route('/')
def home():
    title = "Recipe Finder"
    prompt = "Enter the ingredients you have (comma-separated):"
    instructions = "Type the ingredients below and press 'Find Recipes' to get suggestions!"
    button_label = "Find Recipes"
    
    messages = []
    if 'flash_messages' in session:
        messages = session.pop('flash_messages')
    
    return flask.render_template(
        'index.html',
        title=title,
        prompt=prompt,
        instructions=instructions,
        button_label=button_label,
        messages=messages
    )

# Update the view_recipes route in app.py
@app.route('/recipes')
def view_recipes():
    try:
        # Get filter parameters
        user_filter = flask.request.args.get('user', '')
        search_query = flask.request.args.get('search', '').lower()
        
        # Fetch all recipes from Firebase
        all_recipes = db.child("recipes").get()
        
        recipes_list = []
        if all_recipes.each() is not None:
            for recipe in all_recipes.each():
                recipe_data = recipe.val()
                recipe_data['id'] = recipe.key()
                
                # Apply user filter if specified
                if user_filter and recipe_data.get('user_email') != user_filter:
                    continue
                
                # Apply search filter if specified
                if search_query:
                    # Search in name, ingredients, and instructions
                    name_match = search_query in recipe_data.get('name', '').lower()
                    ingredients_match = any(search_query in ing.lower() for ing in recipe_data.get('ingredients', []))
                    instructions_match = search_query in recipe_data.get('instructions', '').lower()
                    
                    if not (name_match or ingredients_match or instructions_match):
                        continue
                    
                recipes_list.append(recipe_data)
        
        return flask.render_template(
            'recipes.html', 
            recipes=recipes_list, 
            user_filter=user_filter,
            search_query=search_query
        )
        
    except Exception as e:
        print(f"Error fetching recipes: {e}")
        return flask.render_template('recipes.html', recipes=[], error="Failed to load recipes")

@app.route('/recipe/<recipe_id>')
def recipe_detail(recipe_id):
    try:
        recipe = db.child("recipes").child(recipe_id).get()
        if recipe.val():
            recipe_data = recipe.val()
            recipe_data['id'] = recipe_id
            
            # Get user ratings and favorites
            user_ratings = db.child("ratings").child(recipe_id).get()
            ratings = []
            if user_ratings.each():
                for rating in user_ratings.each():
                    ratings.append(rating.val())
            
            # Calculate average rating
            if ratings:
                avg_rating = sum(r['rating'] for r in ratings) / len(ratings)
                recipe_data['avg_rating'] = round(avg_rating, 1)
            else:
                recipe_data['avg_rating'] = 0
                
            # Check if current user has rated or favorited
            user = session.get('user')
            if user:
                user_rating = db.child("ratings").child(recipe_id).child(user['uid']).get()
                user_favorite = db.child("favorites").child(user['uid']).child(recipe_id).get()
                user_bookmark = db.child("bookmarks").child(user['uid']).child(recipe_id).get()
                
                recipe_data['user_rated'] = user_rating.val() is not None
                recipe_data['user_favorited'] = user_favorite.val() is not None
                recipe_data['user_bookmarked'] = user_bookmark.val() is not None
            else:
                recipe_data['user_rated'] = False
                recipe_data['user_favorited'] = False
                recipe_data['user_bookmarked'] = False
                
            return flask.render_template('recipe_detail.html', recipe=recipe_data)
        else:
            return flask.render_template('recipe_detail.html', error="Recipe not found")
    except Exception as e:
        print(f"Error fetching recipe: {e}")
        return flask.render_template('recipe_detail.html', error="Failed to load recipe")

@app.route('/upload', methods=['GET', 'POST'])
def upload_recipe():
    # Check if user is logged in and is chef or admin
    user = session.get('user')
    if not user:
        flask.flash('Please log in to upload recipes', 'warning')
        return flask.redirect('/login')
    
    if user.get('role') not in ['chef', 'admin']:
        flask.flash('Only chefs can upload recipes', 'warning')
        return flask.redirect('/')
    
    if flask.request.method == 'POST':
        try:
            # Get form data
            recipe_name = flask.request.form.get('recipe_name', '').strip()
            ingredients = flask.request.form.get('ingredients', '').strip()
            instructions = flask.request.form.get('instructions', '').strip()
            cooking_time = flask.request.form.get('cooking_time', '').strip()
            difficulty = flask.request.form.get('difficulty', 'Medium').strip()
            
            # Validation errors list
            errors = []
            
            # Validate Recipe Name
            if not recipe_name:
                errors.append("Recipe name is required")
            elif len(recipe_name) < 2:
                errors.append("Recipe name must be at least 2 characters long")
            elif len(recipe_name) > 100:
                errors.append("Recipe name cannot exceed 100 characters")
            
            # Validate Ingredients
            if not ingredients:
                errors.append("Ingredients are required")
            else:
                # Split and clean ingredients
                ingredient_list = [ingredient.strip() for ingredient in ingredients.split(',') if ingredient.strip()]
                if len(ingredient_list) == 0:
                    errors.append("Please provide at least one valid ingredient")
                elif len(ingredient_list) > 50:
                    errors.append("Too many ingredients (maximum 50)")
                else:
                    # Validate each ingredient
                    for i, ingredient in enumerate(ingredient_list):
                        if len(ingredient) > 100:
                            errors.append(f"Ingredient #{i+1} is too long (max 100 characters)")
                        if any(char in ingredient for char in ['<', '>', ';', '{', '}']):
                            errors.append(f"Ingredient #{i+1} contains invalid characters")
            
            # Validate Instructions
            if instructions:
                if len(instructions) < 10:
                    errors.append("Instructions should be at least 10 characters long if provided")
                elif len(instructions) > 2000:
                    errors.append("Instructions are too long (maximum 2000 characters)")
                # Check for suspicious content
                suspicious_keywords = ['<script', 'javascript:', 'onload=', 'onerror=']
                if any(keyword in instructions.lower() for keyword in suspicious_keywords):
                    errors.append("Instructions contain potentially unsafe content")
            
            # Validate Cooking Time
            if cooking_time:
                try:
                    cooking_time_int = int(cooking_time)
                    if cooking_time_int <= 0:
                        errors.append("Cooking time must be a positive number")
                    elif cooking_time_int > 1440:  # 24 hours in minutes
                        errors.append("Cooking time cannot exceed 24 hours (1440 minutes)")
                except ValueError:
                    errors.append("Cooking time must be a valid number")
            else:
                cooking_time_int = None
            
            # Validate Difficulty
            valid_difficulties = ['Easy', 'Medium', 'Hard']
            if difficulty not in valid_difficulties:
                errors.append("Please select a valid difficulty level")
            
            # If there are validation errors, return them
            if errors:
                return flask.render_template(
                    'upload.html',
                    error="Please fix the following errors:",
                    errors=errors,
                    recipe_name=recipe_name,
                    ingredients=ingredients,
                    instructions=instructions,
                    cooking_time=cooking_time,
                    difficulty=difficulty,
                    success=False
                )
            
            # Prepare recipe data (all data is now validated)
            recipe_data = {
                'name': recipe_name,
                'ingredients': ingredient_list,
                'instructions': instructions,
                'cooking_time': cooking_time_int,
                'difficulty': difficulty,
                'created_at': time.time(),
                'created_at_readable': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'user_id': user['uid'],
                'user_email': user['email'],
                'user_role': user.get('role', 'chef')
            }
            
            # Remove None values
            recipe_data = {k: v for k, v in recipe_data.items() if v is not None}
            
            # Save to Firebase Realtime Database
            db.child("recipes").push(recipe_data)
            
            # Show success notification
            return flask.render_template(
                'upload.html',
                success=True,
                message="Recipe uploaded successfully! 🎉",
                recipe_name=recipe_name
            )
            
        except Exception as e:
            print(f"Error uploading recipe: {e}")
            return flask.render_template(
                'upload.html',
                error=f"An unexpected error occurred: {str(e)}",
                success=False
            )
    
    # GET request - show upload form
    return flask.render_template('upload.html', success=None)

# Rating system
@app.route('/rate_recipe/<recipe_id>', methods=['POST'])
def rate_recipe(recipe_id):
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to rate recipes'})
    
    user = session['user']
    rating = int(flask.request.json.get('rating', 0))
    
    if rating < 1 or rating > 5:
        return flask.jsonify({'success': False, 'error': 'Rating must be between 1 and 5'})
    
    try:
        # Check if user already rated this recipe
        existing_rating = db.child("ratings").child(recipe_id).child(user['uid']).get()
        if existing_rating.val():
            return flask.jsonify({'success': False, 'error': 'You have already rated this recipe'})
        
        # Save rating
        rating_data = {
            'user_id': user['uid'],
            'user_email': user['email'],
            'rating': rating,
            'rated_at': time.time()
        }
        db.child("ratings").child(recipe_id).child(user['uid']).set(rating_data)
        
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})

# Favorite system
@app.route('/favorite_recipe/<recipe_id>', methods=['POST'])
def favorite_recipe(recipe_id):
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to favorite recipes'})
    
    user = session['user']
    
    try:
        # Check if user already favorited this recipe
        existing_favorite = db.child("favorites").child(user['uid']).child(recipe_id).get()
        if existing_favorite.val():
            return flask.jsonify({'success': False, 'error': 'You have already favorited this recipe'})
        
        # Save favorite
        favorite_data = {
            'recipe_id': recipe_id,
            'favorited_at': time.time()
        }
        db.child("favorites").child(user['uid']).child(recipe_id).set(favorite_data)
        
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})

# Bookmark system
@app.route('/bookmark_recipe/<recipe_id>', methods=['POST'])
def bookmark_recipe(recipe_id):
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to bookmark recipes'})
    
    user = session['user']
    
    try:
        # Toggle bookmark (unlike favorite, bookmarks can be toggled)
        existing_bookmark = db.child("bookmarks").child(user['uid']).child(recipe_id).get()
        
        if existing_bookmark.val():
            # Remove bookmark
            db.child("bookmarks").child(user['uid']).child(recipe_id).remove()
            return flask.jsonify({'success': True, 'bookmarked': False})
        else:
            # Add bookmark
            bookmark_data = {
                'recipe_id': recipe_id,
                'bookmarked_at': time.time()
            }
            db.child("bookmarks").child(user['uid']).child(recipe_id).set(bookmark_data)
            return flask.jsonify({'success': True, 'bookmarked': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})

# Bookmarks page
@app.route('/bookmarks')
def view_bookmarks():
    if not session.get('user'):
        flask.flash('Please log in to view your bookmarks', 'warning')
        return flask.redirect('/login')
    
    user = session['user']
    
    try:
        # Get user's bookmarks
        user_bookmarks = db.child("bookmarks").child(user['uid']).get()
        bookmarked_recipes = []
        
        if user_bookmarks.each():
            for bookmark in user_bookmarks.each():
                recipe_id = bookmark.key()
                recipe = db.child("recipes").child(recipe_id).get()
                if recipe.val():
                    recipe_data = recipe.val()
                    recipe_data['id'] = recipe_id
                    bookmarked_recipes.append(recipe_data)
        
        return flask.render_template('bookmarks.html', recipes=bookmarked_recipes)
    except Exception as e:
        print(f"Error fetching bookmarks: {e}")
        return flask.render_template('bookmarks.html', recipes=[], error="Failed to load bookmarks")

# Update the calendar route to load user's calendar events
@app.route('/calendar')
def calendar():
    if not session.get('user'):
        flask.flash('Please log in to view your calendar', 'warning')
        return flask.redirect('/login')
    
    user = session['user']
    
    try:
        # Load user's calendar events
        user_calendar = db.child("calendar").child(user['uid']).get()
        calendar_events = []
        
        if user_calendar and user_calendar.each():
            for event in user_calendar.each():
                event_data = event.val()
                event_data['id'] = event.key()
                
                # Get recipe details based on source
                if event_data.get('source') == 'spoonacular':
                    # For Spoonacular recipes, we have the title stored directly
                    event_data['recipe_name'] = event_data.get('recipe_title', 'Online Recipe')
                else:
                    # For uploaded recipes, get from recipes collection
                    recipe = db.child("recipes").child(event_data['recipe_id']).get()
                    if recipe and recipe.val():
                        event_data['recipe_name'] = recipe.val().get('name', 'Unknown Recipe')
                    else:
                        event_data['recipe_name'] = 'Unknown Recipe'
                        
                calendar_events.append(event_data)
        
        return flask.render_template('calendar.html', calendar_events=calendar_events)
    except Exception as e:
        print(f"Error loading calendar: {e}")
        return flask.render_template('calendar.html', calendar_events=[])

# Add this to app.py
@app.route('/remove_from_calendar', methods=['POST'])
def remove_from_calendar():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to manage your calendar'})
    
    user = session['user']
    event_id = flask.request.json.get('event_id')
    
    try:
        # Remove event from user's calendar
        db.child("calendar").child(user['uid']).child(event_id).remove()
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})
    
# Add a JSON endpoint for recipes
@app.route('/recipes.json')
def recipes_json():
    if not session.get('user'):
        return flask.jsonify([])
    
    user = session['user']
    
    try:
        all_recipes = []
        
        # Get uploaded recipes
        uploaded_recipes = db.child("recipes").get()
        if uploaded_recipes and uploaded_recipes.each():
            for recipe in uploaded_recipes.each():
                recipe_data = recipe.val()
                recipe_data['id'] = recipe.key()
                recipe_data['source'] = 'uploaded'
                all_recipes.append(recipe_data)
        
        # Get saved online recipes
        saved_recipes = db.child("saved_recipes").child(user['uid']).get()
        if saved_recipes and saved_recipes.each():
            for saved_recipe in saved_recipes.each():
                recipe_data = saved_recipe.val()
                recipe_data['id'] = saved_recipe.key()
                recipe_data['source'] = 'spoonacular'
                all_recipes.append(recipe_data)
        
        return flask.jsonify(all_recipes)
        
    except Exception as e:
        print(f"Error fetching recipes: {e}")
        return flask.jsonify([])

@app.route('/add_to_calendar', methods=['POST'])
def add_to_calendar():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to add recipes to calendar'})
    
    user = session['user']
    recipe_id = flask.request.json.get('recipe_id')
    day = flask.request.json.get('day')
    time_slot = flask.request.json.get('time')
    source = flask.request.json.get('source', 'uploaded')
    
    try:
        # Get recipe name based on source
        recipe_name = "Unknown Recipe"
        if source == 'uploaded':
            recipe = db.child("recipes").child(recipe_id).get()
            if recipe and recipe.val():
                recipe_name = recipe.val().get('name', 'Unknown Recipe')
        elif source == 'spoonacular':
            saved_recipe = db.child("saved_recipes").child(user['uid']).child(recipe_id).get()
            if saved_recipe and saved_recipe.val():
                recipe_name = saved_recipe.val().get('name', 'Online Recipe')
        
        calendar_data = {
            'recipe_id': recipe_id,
            'recipe_title': recipe_name,
            'day': day,
            'time': time_slot,
            'added_at': time.time(),
            'source': source
        }
        
        # Save to user's calendar
        result = db.child("calendar").child(user['uid']).push(calendar_data)
        event_id = result['name']
        
        return flask.jsonify({'success': True, 'event_id': event_id})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})



# Also update the regular shopping list route
@app.route('/shopping_list/<recipe_id>')
def shopping_list(recipe_id):
    try:
        recipe = db.child("recipes").child(recipe_id).get()
        if not recipe.val():
            return flask.render_template('shopping_list.html', error="Recipe not found")
        
        recipe_data = recipe.val()
        recipe_data['id'] = recipe_id
        
        return flask.render_template(
            'shopping_list.html', 
            recipe=recipe_data,
            google_maps_api_key=GOOGLE_MAPS_API_KEY
        )
    except Exception as e:
        print(f"Error loading shopping list: {e}")
        return flask.render_template('shopping_list.html', error="Failed to load shopping list")
    

@app.route('/saved_recipes')
def saved_recipes():
    if not session.get('user'):
        flask.flash('Please log in to view your saved recipes', 'warning')
        return flask.redirect('/login')
    
    user = session['user']
    
    try:
        # Get user's saved recipes from both sources
        saved_recipes_list = []
        
        # Get uploaded recipes created by this user
        all_recipes = db.child("recipes").get()
        if all_recipes and all_recipes.each():
            for recipe in all_recipes.each():
                recipe_data = recipe.val()
                if recipe_data.get('user_id') == user['uid']:
                    recipe_data['id'] = recipe.key()
                    recipe_data['source'] = 'uploaded'
                    recipe_data['saved_at'] = recipe_data.get('created_at', time.time())
                    saved_recipes_list.append(recipe_data)
        
        # Get saved online recipes - FIXED: Use the correct path
        saved_online_recipes = db.child("saved_recipes").child(user['uid']).get()
        if saved_online_recipes and saved_online_recipes.each():
            for saved_recipe in saved_online_recipes.each():
                recipe_data = saved_recipe.val()
                recipe_data['id'] = saved_recipe.key()
                recipe_data['source'] = 'spoonacular'
                saved_recipes_list.append(recipe_data)
        
        # Sort by saved date (newest first)
        saved_recipes_list.sort(key=lambda x: x.get('saved_at', 0), reverse=True)
        
        return flask.render_template('saved_recipes.html', recipes=saved_recipes_list)
    except Exception as e:
        print(f"Error fetching saved recipes: {e}")
        return flask.render_template('saved_recipes.html', recipes=[], error="Failed to load saved recipes")


# Update the favourites route in app.py
@app.route('/favourites')
def favourites():
    if not session.get('user'):
        flask.flash('Please log in to view your favourites', 'warning')
        return flask.redirect('/login')
    
    user = session['user']
    
    try:
        # Get user's favourites from both sources
        favourite_recipes = []
        
        # Get uploaded recipe favourites
        user_favourites = db.child("favorites").child(user['uid']).get()
        if user_favourites and user_favourites.each():
            for fav in user_favourites.each():
                recipe_id = fav.key()
                recipe = db.child("recipes").child(recipe_id).get()
                if recipe and recipe.val():
                    recipe_data = recipe.val()
                    recipe_data['id'] = recipe_id
                    recipe_data['source'] = 'uploaded'
                    recipe_data['favourited_at'] = fav.val().get('favorited_at', 0)
                    favourite_recipes.append(recipe_data)
        
        # Get Spoonacular recipe favourites
        spoonacular_favourites = db.child("spoonacular_favorites").child(user['uid']).get()
        if spoonacular_favourites and spoonacular_favourites.each():
            for fav in spoonacular_favourites.each():
                fav_data = fav.val()
                recipe_data = {
                    'id': fav_data['recipe_id'],
                    'name': fav_data['recipe_title'],
                    'source': 'spoonacular',
                    'favourited_at': fav_data.get('favorited_at', 0)
                }
                favourite_recipes.append(recipe_data)
        
        # Sort by favourite date (newest first)
        favourite_recipes.sort(key=lambda x: x.get('favourited_at', 0), reverse=True)
        
        return flask.render_template('favourites.html', recipes=favourite_recipes)
        
    except Exception as e:
        print(f"Error fetching favourites: {e}")
        # Only show error if there's an actual system error, not just empty results
        return flask.render_template('favourites.html', recipes=[], error="Failed to load favourites due to a system error")

# Remove saved recipe
@app.route('/remove_saved_recipe', methods=['POST'])
def remove_saved_recipe():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to manage saved recipes'})
    
    user = session['user']
    data = flask.request.json
    recipe_id = data.get('recipe_id')
    recipe_source = data.get('recipe_source')
    
    try:
        if recipe_source == 'spoonacular':
            # Remove from Spoonacular saved
            db.child("spoonacular_saved").child(user['uid']).child(recipe_id).remove()
        else:
            # Remove uploaded recipe
            db.child("recipes").child(recipe_id).remove()
        
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})

# Unfavorite recipe
@app.route('/unfavorite_recipe', methods=['POST'])
def unfavorite_recipe():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to manage favourites'})
    
    user = session['user']
    recipe_id = flask.request.json.get('recipe_id')
    
    try:
        db.child("favorites").child(user['uid']).child(recipe_id).remove()
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})

# Unfavorite Spoonacular recipe
@app.route('/unfavorite_spoonacular_recipe', methods=['POST'])
def unfavorite_spoonacular_recipe():
    if not session.get('user'):
        return flask.jsonify({'success': False, 'error': 'Please log in to manage favourites'})
    
    user = session['user']
    recipe_id = flask.request.json.get('recipe_id')
    
    try:
        db.child("spoonacular_favorites").child(user['uid']).child(recipe_id).remove()
        return flask.jsonify({'success': True})
    except Exception as e:
        return flask.jsonify({'success': False, 'error': str(e)})


# Update the results route in app.py to use a template
@app.route('/results', methods=['POST'])
def results():
    # Get ingredients from form submission
    ingredients_input = flask.request.form.get('ingredients', '')
    ingredients_list = [item.strip() for item in ingredients_input.split(',') if item.strip()]
    
    if not ingredients_list:
        return flask.render_template(
            'results.html',
            recipes=[],
            ingredients_input=ingredients_input,
            ingredients_list=[],
            error="Please enter at least one ingredient"
        )
    
    # Get recipes from API
    recipes = get_recipes_by_ingredients(ingredients_list)
    
    return flask.render_template(
        'results.html',
        recipes=recipes,
        ingredients_input=ingredients_input,
        ingredients_list=ingredients_list
    )

@app.route('/test_api')
def test_api():
    test_recipes = get_recipes_by_ingredients(['chicken', 'rice'], number=2)
    return flask.jsonify({
        'api_working': len(test_recipes) > 0,
        'recipes_found': len(test_recipes),
        'api_key_set': bool(API_KEY)
    })

if __name__ == '__main__':
    app.run(debug=True) # debug=True enables debug mode for development