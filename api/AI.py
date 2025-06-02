from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from .utils import Preprocess,get_all_recipes,get_recipe_info_by_id_or_user
from .serializers import RecipeSerializer
import pandas as pd
import numpy as np

def recommend_similar_recipes(base_recipe_id, top_n=5,min_similarity=0.3):
    p=Preprocess()

    all_recipes_df = get_all_recipes()
    all_recipes_df = p.preprocess_recipes(all_recipes_df)



    base_df = get_recipe_info_by_id_or_user(recipe_id=base_recipe_id)
    if base_df.empty:
        return pd.DataFrame()
    base_df = p.preprocess_recipes(base_df)
 
    def combine_fields(row):
        return " ".join([
            row["Description"],
            " ".join(row["Ingredients"]),
            " ".join(row["Ingredients"]),
            row["Cuisine"],
            row["Dietary Restrictions"],
            " ".join(row["Instructions"]),
            " ".join(row["Equipment"]),
            " ".join(row["Course"]),
            " ".join(row["Course"])
        ])

    all_recipes_df["combined"] = all_recipes_df.apply(combine_fields, axis=1)
    base_combined = base_df.apply(combine_fields, axis=1).values[0]


    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_recipes_df["combined"])
    base_vector = vectorizer.transform([base_combined])


    cosine_sim = cosine_similarity(base_vector, tfidf_matrix).flatten()

  
    all_recipes_df["similarity"] = cosine_sim
    all_recipes_df = all_recipes_df[all_recipes_df["ID"] != base_recipe_id]
    all_recipes_df = all_recipes_df[all_recipes_df["similarity"] >= min_similarity]

    if all_recipes_df.empty:
        return pd.DataFrame()

    if len(all_recipes_df)<1:
        return pd.DataFrame()


    base_info = base_df.iloc[0]
    base_time = base_info["Total_time"]
    base_nutrition = base_info["Nutritional Info"]

    def extract_nutrition_fields(df):
        df["calories"] = [info["calories"] for info in df["Nutritional Info"]]
        df["protein"] = [info["protein"] for info in df["Nutritional Info"]]
        df["carbs"] = [info["carbs"] for info in df["Nutritional Info"]]
        df["fat"] = [info["fat"] for info in df["Nutritional Info"]]
        return df

    all_recipes_df = extract_nutrition_fields(all_recipes_df)

 
    scaler = MinMaxScaler()
    all_recipes_df[["Total_time", "calories", "protein", "carbs", "fat"]] = scaler.fit_transform(
        all_recipes_df[["Total_time", "calories", "protein", "carbs", "fat"]]
    )


    base_time_scaled = scaler.transform([[base_time, base_nutrition["calories"],
                                          base_nutrition["protein"],
                                          base_nutrition["carbs"],
                                          base_nutrition["fat"]]])[0]

    all_recipes_df["score"] = (
        all_recipes_df["similarity"] * 0.7
        + (1 - abs(all_recipes_df["Total_time"] - base_time_scaled[0])) * 0.1
        + (1 - abs(all_recipes_df["calories"] - base_time_scaled[1])) * 0.1
        + (1 - abs(all_recipes_df["protein"] - base_time_scaled[2])) * 0.1
        + (1 - abs(all_recipes_df["carbs"] - base_time_scaled[3])) * 0.1
        + (1 - abs(all_recipes_df["fat"] - base_time_scaled[4])) * 0.1
    )

    top_matches = all_recipes_df.sort_values(by="score", ascending=False).head(top_n)

    return top_matches.drop(columns=["combined", "similarity", "score"])


def get_combined_text(df):
    return (
        df['Ingredients'].astype(str) + ' ' +
        df['Ingredients'].astype(str) + ' ' +
        df['Dietary Restrictions'].astype(str) + ' ' +
        df['Dietary Restrictions'].astype(str) + ' ' +  
        df['Cuisine'].astype(str)  
    )


def start(username,min_similarity=0.3):
    p=Preprocess()
    df=get_all_recipes()
    if get_recipe_info_by_id_or_user(username=username).empty:
        return pd.DataFrame()
    userdf=get_recipe_info_by_id_or_user(username=username)
    df=p.preprocess_recipes(df)
    userdf=p.preprocess_recipes(userdf)
    
   
    df['combined_text'] = get_combined_text(df)
    userdf['combined_text'] = get_combined_text(userdf)
        
    all_texts = pd.concat([df['combined_text'], userdf['combined_text']])
    vectorizer = TfidfVectorizer(stop_words='english')
    vectorizer.fit(all_texts)

    all_vecs = vectorizer.transform(df['combined_text'])
    user_vecs = vectorizer.transform(userdf['combined_text'])

    user_profile = np.asarray(user_vecs.mean(axis=0)).reshape(1, -1)

    similarities = cosine_similarity(all_vecs, user_profile).flatten()

    df['Similarity'] = similarities
    recommended_df = df.sort_values(by='Similarity', ascending=False).reset_index(drop=True)

    saved_ids = set(userdf['ID'])  
    recommended_df = recommended_df[~recommended_df['ID'].isin(saved_ids)].reset_index(drop=True)

    recommended_df = recommended_df[recommended_df['Similarity'] >= min_similarity].reset_index(drop=True)


    avg_total_time = userdf["Total_time"].mean()
    avg_difficulty = userdf["Difficulty Level"].mean()

    recommended_df["time_distance"] = (recommended_df["Total_time"] - avg_total_time).abs()
    recommended_df["difficulty_distance"] = (recommended_df["Difficulty Level"] - avg_difficulty).abs()

    final_recommendations = recommended_df.sort_values(
        by=["Similarity", "difficulty_distance", "time_distance"],
        ascending=[False, True, True] 
    ).reset_index(drop=True)

    return final_recommendations


def generate_recipe_by_ings(ings: list[str], request=None):
    p = Preprocess()
    all_recipes_df = get_all_recipes()
    
    # Preprocess ingredients
    processed_df = p.preprocess_recipes(all_recipes_df)
    all_ingredients = processed_df['Ingredients']  # List of strings

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer()
    all_vecs = vectorizer.fit_transform(all_ingredients)  # All recipes
    user_vec = vectorizer.transform(ings)  # User input

    # Compute cosine similarity
    cosine_sim = cosine_similarity(all_vecs, user_vec).flatten()

    # Sort recipes by similarity
    sorted_indices = cosine_sim.argsort()[::-1]
    matching_ids = [processed_df.iloc[i]['ID'] for i in sorted_indices if cosine_sim[i] > 0]

    # Get actual Recipe queryset in correct order
    from .models import Recipe  # Adjust as needed
    recipe_qs = Recipe.objects.filter(id__in=matching_ids)
    
    # Maintain the sorted order
    id_to_recipe = {recipe.id: recipe for recipe in recipe_qs}
    sorted_recipes = [id_to_recipe[recipe_id] for recipe_id in matching_ids if recipe_id in id_to_recipe]

    # Serialize
    serializer = RecipeSerializer(sorted_recipes, many=True, context={"request": request})
    return serializer.data



