import pandas as pd
import re
from .models import Recipe,CustomUser,SavedRecipe,Ingredient
import numpy as np # Replace with your actual app name
import inflect
import random
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

p = inflect.engine()


class Preprocess:

    def __preprocess_ingredients(self,x):
        x=list(x)
        for i in range(len(x)):
            x[i] = re.sub(r'\([^)]*\)', '', x[i])
            x[i]=x[i].split(",")
            x[i]=[normalize_ingredient_name(e) for e in x[i]]
            x[i]=" ".join(x[i]).lower()
        return x

                
        return [" ".join(i.split(",")).lower() for i in x]

    def preprocess_time(self,x):
        time=[]
        for i in x:
            if "hour" in i and "minute" in i:
                res=int(re.findall(r"\d+",i)[0])*60+int(re.findall(r"\d+",i)[1])
            elif "hour" in i and not "minute" in i:
                res=int(re.findall(r"\d+",i)[0])*60
            else:
                res=int(re.findall(r"\d+",i)[0])
            time.append(res)
        return time

    def __preprocess_cuisine(self,x):
        return [i.name.lower() for i in x]

    def preprocess_difflevel(self,x):
        diff=[]
        for i in x:
            if i=="Medium":
                res=2
            elif i=="Hard":
                res=3
            else:
                res=1
            diff.append(res)
        return diff
    
    
    def __preprocess_instructions(self,x):
        ins=[]
        for i in x:
            z=" ".join(re.findall(r"[a-zA-Z0-9]+"," ".join(i))).lower()
            ins.append(z)
        return ins
    
    def __preprocess_description(self,x):
        return [" ".join(re.findall(r"[a-zA-Z0-9]+","".join(i))) for i in x]

    def __preprocess_equipments(self,x):
        return [" ".join(i).lower() for i in x]

    def __preprocess_course(self,x):
        return [i.name.lower()  for i in x]
    
    def __get_nutritional_info(self,x):
        l=[]
        for i in x:
            d={}
            d['calories']=int(re.findall(r"\d+",i['calories'])[0])
            d['protein']=int(re.findall(r"\d+",i['protein'])[0])
            d['carbs']=int(re.findall(r"\d+",i['carbs'])[0])
            d['fat']=int(re.findall(r"\d+",i['fat'])[0])
            l.append(d)
        return l
    
        
    def preprocess_recipes(self,df):
        df["ID"]=df["ID"]
        df["Description"]=self.__preprocess_description(df["Description"])
        df["Ingredients"]=self.__preprocess_ingredients(df["Ingredients"])
        df["Total_time"]=self.preprocess_time(df["Total_time"])
        df['Cuisine']=self.__preprocess_cuisine(df["Cuisine"])
        df['Course']=self.__preprocess_course(df["Course"])
        df["Difficulty Level"]=self.preprocess_difflevel(df["Difficulty Level"])
        if "Dietary Restrictions" in df.columns and df["Dietary Restrictions"].notna().any():
            df["Dietary Restrictions"] = df["Dietary Restrictions"].apply(
            lambda x: " ".join(x).lower() if isinstance(x, list) else x
        )

        df["Instructions"]=self.__preprocess_instructions(df["Instructions"])
        df["Equipment"]=self.__preprocess_equipments(df["Equipment"])
        df["Nutritional Info"]=self.__get_nutritional_info(df["Nutritional Info"])

        return df


def get_recipe_info_by_id_or_user(recipe_id=None, username=None):
    try:
        # Case 1: Get recipe by ID
        if recipe_id is not None:
            recipe = Recipe.objects.get(id=recipe_id)

            ingredient_list = ",".join([
                f"{ing.ingredient}" for ing in recipe.ingredients.all()
            ])
            instructions = [inst.step for inst in recipe.instructions.all()]
            equipment = [eq.name for eq in recipe.equipment.all()]
            nutritional_info = {}

            if hasattr(recipe, "nutritional_information"):
                ni = recipe.nutritional_information
                nutritional_info = {
                    "calories": ni.calories,
                    "protein": ni.protein,
                    "carbs": ni.carbs,
                    "fat": ni.fat
                }

            data = [{
                "ID": recipe.id,
                "Title": recipe.title,
                "Description": recipe.description,
                "Total_time": recipe.total_time,
                "Difficulty Level": recipe.difficulty_level,
                "Cuisine": recipe.cuisine,
                "Course": recipe.course,
                "Dietary Restrictions": [dr.name for dr in recipe.dietary_restrictions.all()],
                "Ingredients": ingredient_list,
                "Instructions": instructions,
                "Equipment": equipment,
                "Nutritional Info": nutritional_info
            }]
            return pd.DataFrame(data)

        # Case 2: Get all saved recipes for a user
        elif username is not None:
            user = CustomUser.objects.get(username=username)
            saved_recipes = SavedRecipe.objects.filter(user=user)

            recipe_rows = []
            for saved_recipe in saved_recipes:
                recipe = saved_recipe.recipe

                ingredient_list = ",".join(
                    [f"{ing.ingredient}" for ing in recipe.ingredients.all()]
                )
                instructions = [inst.step for inst in recipe.instructions.all()]
                equipment = [eq.name for eq in recipe.equipment.all()]
                nutritional_info = {}
                if hasattr(recipe, "nutritional_information"):
                    ni = recipe.nutritional_information
                    nutritional_info = {
                        "calories": ni.calories,
                        "protein": ni.protein,
                        "carbs": ni.carbs,
                        "fat": ni.fat
                    }

                recipe_rows.append([
                    recipe.id,
                    recipe.title,
                    recipe.description,
                    recipe.total_time,
                    recipe.difficulty_level,
                    recipe.cuisine,
                    recipe.course,
                    recipe.dietary_restrictions,
                    ingredient_list,
                    instructions,
                    equipment,
                    nutritional_info
                ])

            columns = [
                "ID", "Title", "Description", "Total_time",
                "Difficulty Level", "Cuisine", "Course",
                "Dietary Restrictions", "Ingredients",
                "Instructions", "Equipment", "Nutritional Info"
            ]
            return pd.DataFrame(recipe_rows, columns=columns)

        else:
            print("Either recipe_id or username must be provided.")
            return pd.DataFrame()

    except Recipe.DoesNotExist:
        print("Recipe not found.")
        return pd.DataFrame()
    except CustomUser.DoesNotExist:
        print("User not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame()

# Function to get all recipes with the same fields as in get_recipe_info_by_id
def get_all_recipes():
    try:
        recipes = Recipe.objects.all()
        recipe_rows = []

        for recipe in recipes:
            data = {
                "ID":recipe.id,
                "Title": recipe.title,
                "Description": recipe.description,
                "Total_time": recipe.total_time,
                "Difficulty Level": recipe.difficulty_level,
                "Cuisine": recipe.cuisine,
                "Course": recipe.course,
                "Dietary Restrictions": [dr.name for dr in recipe.dietary_restrictions.all()],
                "Ingredients":",".join([
                f"{ing.ingredient}"
                for ing in recipe.ingredients.all()
            ]),
                "Instructions": [inst.step for inst in recipe.instructions.all()],
                "Equipment": [eq.name for eq in recipe.equipment.all()],
                "Nutritional Info": {},
            }

            # Add nutritional info if exists
            if hasattr(recipe, "nutritional_information"):
                ni = recipe.nutritional_information
                data["Nutritional Info"] = {
                    "calories": ni.calories,
                    "protein": ni.protein,
                    "carbs": ni.carbs,
                    "fat": ni.fat
                }

            # Append recipe data to rows
            recipe_rows.append(data)

        # Create DataFrame
        df = pd.DataFrame(recipe_rows)

        return df

    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame()  


def normalize_ingredient_name(name):

    name = name.strip().lower()
    words = name.split()

    # Only singularize last word (usually the noun)
    if words:
        words[-1] = p.singular_noun(words[-1]) or words[-1]
    return " ".join(words)



def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(email, code):
    subject = 'Verify Your Email Address - YourAppName'
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [email]

    context = {
        'code': code,
        'support_email': 'zynoverse02@gmail.com',
        'app_name': 'Ai based Recipe App',
    }

    # Render HTML template with context
    html_content = render_to_string('verification_email.html', context)

    # Plain text fallback
    text_content = f"Your verification code is: {code}\nIf you didn't request this, please ignore this email."

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def generate_reset_code():
    return str(random.randint(100000, 999999))

def send_reset_email(email, code):
    subject = "Password Reset Code"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [email]
    
    # Render HTML template with context
    html_content = render_to_string("reset_password_email.html", {"code": code})
    text_content = f"Your password reset code is: {code}"

    # Create email
    email_message = EmailMultiAlternatives(subject, text_content, from_email, to)
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()